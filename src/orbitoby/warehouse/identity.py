"""Conservative object identity and provenance-preserving local catalogue.

Only explicit identifiers establish identity; names never do. Conflicting
claims remain queryable as unlinked source records rather than corrupting a
previously resolved object. All writes for an ingestion are transactional.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from uuid import uuid4


SCHEMA = """
CREATE TABLE IF NOT EXISTS objects (
    object_id VARCHAR PRIMARY KEY,
    norad_id BIGINT UNIQUE,
    cospar_id VARCHAR UNIQUE,
    name VARCHAR,
    created_at TIMESTAMPTZ DEFAULT current_timestamp
);
CREATE TABLE IF NOT EXISTS object_identifiers (
    namespace VARCHAR,
    identifier VARCHAR,
    object_id VARCHAR NOT NULL,
    PRIMARY KEY (namespace, identifier)
);
CREATE TABLE IF NOT EXISTS source_records (
    record_id VARCHAR PRIMARY KEY,
    artifact_id VARCHAR NOT NULL,
    row_index BIGINT NOT NULL,
    source VARCHAR NOT NULL,
    dataset VARCHAR NOT NULL,
    object_id VARCHAR,
    retrieved_at TIMESTAMPTZ NOT NULL,
    data JSON NOT NULL,
    identity_status VARCHAR NOT NULL,
    identity_detail VARCHAR,
    UNIQUE (artifact_id, row_index)
);
CREATE TABLE IF NOT EXISTS object_properties (
    record_id VARCHAR NOT NULL,
    object_id VARCHAR NOT NULL,
    property VARCHAR NOT NULL,
    value JSON NOT NULL,
    PRIMARY KEY (record_id, property)
);
CREATE TABLE IF NOT EXISTS object_redirects (
    old_object_id VARCHAR PRIMARY KEY,
    object_id VARCHAR NOT NULL
);
CREATE INDEX IF NOT EXISTS source_object_lookup ON source_records(object_id);
CREATE INDEX IF NOT EXISTS property_lookup ON object_properties(object_id, property);
"""


def dumps(value):
    def encode(item):
        if isinstance(item, (date, datetime)):
            return item.isoformat()
        raise TypeError(f"Unsupported record value: {type(item).__name__}")
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=encode,
                      allow_nan=False)


def norad(value):
    """Accept positive decimal catalogue numbers; reject lossy conversions."""
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if not re.fullmatch(r"[0-9]{1,9}", text) or int(text) == 0:
        return None
    return int(text)


def cospar(value):
    if not isinstance(value, str):
        return None
    text = re.sub(r"\s+", "", value).upper()
    match = re.fullmatch(r"(\d{4})-?(\d{3})([A-HJ-NP-Z]{1,3})", text)
    if not match or int(match[2]) == 0 or int(match[1]) < 1957:
        return None
    return f"{match[1]}-{match[2]}{match[3]}"


def first(row, *keys):
    for key in keys:
        value = row.get(key)
        if value is not None and value != "" and value != "-":
            return value
    return None


def claims(source, dataset, row):
    """Extract explicit identifiers from object records, never nested parents."""
    aliases = []
    n = c = name = None
    if source == "spacetrack":
        n, c, name = row.get("norad_id"), row.get("object_id"), row.get("object_name")
    elif source == "celestrak":
        n = row.get("NORAD_CAT_ID")
        c = first(row, "OBJECT_ID", "INTLDES")
        name = row.get("OBJECT_NAME")
    elif source == "satnogs":
        n, c = row.get("norad_cat_id"), row.get("cospar_id")
        name = row.get("name") if dataset == "satellites" else None
        sat_id = row.get("sat_id")
        if sat_id:
            aliases.append(("satnogs", str(sat_id)))
    elif source == "gcat":
        jcat = str(first(row, "JCAT", "#JCAT") or "").strip()
        if jcat:
            aliases.append(("gcat", jcat))
        # Auxiliary components may share the parent's SATCAT/Piece. Only the
        # standard catalogue's S identifiers establish cross-source identity.
        if jcat.startswith("S"):
            n, c = row.get("Satcat"), row.get("Piece")
        name = row.get("Name")
    elif source == "launchlibrary" and dataset == "payloads":
        n = first(row, "norad_id", "norad_cat_id")
        c = first(row, "cospar_id", "international_designator")
        name = row.get("name")
        if row.get("id") is not None:
            aliases.append(("launchlibrary:payload", str(row["id"])))
    return norad(n), cospar(c), name, aliases


def properties(source, row):
    """Keep native fields and add a small set of explicitly mapped properties."""
    result = {str(k): v for k, v in row.items() if v is not None}
    mappings = {
        "celestrak": {"object_type": "OBJECT_TYPE", "country": "COUNTRY_CODE"},
        "gcat": {"country": "State", "mass_kg": "Mass", "status": "Status"},
        "satnogs": {"status": "status"},
    }
    for target, key in mappings.get(source, {}).items():
        value = row.get(key)
        if value is None or value == "-":
            continue
        if target == "mass_kg":
            try:
                value = float(value)
            except (ValueError, TypeError):
                continue
        result[target] = value
    return result


class IdentityStore:
    def __init__(self, con):
        self.con = con

    def resolve(self, source, dataset, row):
        n, c, name, aliases = claims(source, dataset, row)
        identifiers = list(aliases)
        if n is not None:
            identifiers.append(("norad", str(n)))
        if c is not None:
            identifiers.append(("cospar", c))
        if not identifiers:
            return None, "unidentified", "No explicit object identifier"
        ids = set()
        for namespace, identifier in identifiers:
            found = self.con.execute(
                "SELECT object_id FROM object_identifiers WHERE namespace=? AND identifier=?",
                [namespace, identifier],
            ).fetchone()
            if found:
                ids.add(found[0])
        existing = [self.con.execute(
            "SELECT object_id, norad_id, cospar_id, name FROM objects WHERE object_id=?", [oid]
        ).fetchone() for oid in sorted(ids)]
        ns = {r[1] for r in existing if r[1] is not None} | ({n} if n else set())
        cs = {r[2] for r in existing if r[2] is not None} | ({c} if c else set())
        if len(ns) > 1 or len(cs) > 1:
            return None, "conflict", "Incompatible NORAD/COSPAR claims"
        if not existing:
            # Source-only identities allow later explicit enrichment without
            # inventing NORAD numbers or using names as keys.
            oid = str(uuid4())
            self.con.execute("INSERT INTO objects(object_id, norad_id, cospar_id, name) VALUES (?,?,?,?)",
                             [oid, n, c, name])
        else:
            oid = existing[0][0]
            for other, _, _, _ in existing[1:]:
                for table in ("source_records", "object_properties", "object_identifiers", "object_redirects"):
                    self.con.execute(f"UPDATE {table} SET object_id=? WHERE object_id=?", [oid, other])
                self.con.execute("INSERT INTO object_redirects VALUES (?,?)", [other, oid])
                self.con.execute("DELETE FROM objects WHERE object_id=?", [other])
            self.con.execute(
                "UPDATE objects SET norad_id=?, cospar_id=?, name=coalesce(name, ?) WHERE object_id=?",
                [next(iter(ns), None), next(iter(cs), None), name, oid],
            )
        for namespace, identifier in identifiers:
            self.con.execute("INSERT OR IGNORE INTO object_identifiers VALUES (?,?,?)", [namespace, identifier, oid])
        return oid, "linked", None

    def ingest(self, records, artifact, *, transaction=True):
        if transaction:
            self.con.execute("BEGIN TRANSACTION")
        try:
            for index, row in enumerate(records):
                record_id = hashlib.sha256(f"{artifact.artifact_id}:{index}".encode()).hexdigest()
                if self.con.execute("SELECT 1 FROM source_records WHERE record_id=?", [record_id]).fetchone():
                    continue
                oid, status, detail = self.resolve(artifact.source, artifact.dataset, row)
                self.con.execute("INSERT INTO source_records VALUES (?,?,?,?,?,?,?,?,?,?)", [
                    record_id, artifact.artifact_id, index, artifact.source, artifact.dataset,
                    oid, artifact.retrieved_at, dumps(row), status, detail,
                ])
                if oid:
                    props = [(record_id, oid, key, dumps(value))
                             for key, value in properties(artifact.source, row).items()]
                    if props:
                        self.con.executemany("INSERT INTO object_properties VALUES (?,?,?,?)", props)
            if transaction:
                self.con.execute("COMMIT")
        except Exception:
            if transaction:
                self.con.execute("ROLLBACK")
            raise
