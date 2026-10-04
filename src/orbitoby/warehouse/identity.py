"""Conservative object identity and provenance-preserving local catalogue.

Only explicit identifiers establish identity; names never do.

Provider-native rows remain preserved in ``source_records.data``.
``object_properties`` stores only a small canonical searchable projection,
rather than duplicating every provider-native field.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
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

CREATE INDEX IF NOT EXISTS source_object_lookup
ON source_records(object_id);

CREATE INDEX IF NOT EXISTS source_dataset_lookup
ON source_records(source, dataset);

CREATE INDEX IF NOT EXISTS property_lookup
ON object_properties(object_id, property);
"""


def dumps(value):
    def encode(item):
        if isinstance(item, (date, datetime)):
            return item.isoformat()

        raise TypeError(f"Unsupported record value: {type(item).__name__}")

    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        default=encode,
        allow_nan=False,
    )


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

    match = re.fullmatch(
        r"(\d{4})-?(\d{3})([A-HJ-NP-Z]{1,3})",
        text,
    )

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
    """Extract explicit identifiers from object records, never names."""
    aliases = []
    n = c = name = None

    if source == "spacetrack":
        n = row.get("norad_id")
        c = row.get("object_id")
        name = row.get("object_name")

    elif source == "celestrak":
        n = row.get("NORAD_CAT_ID")
        c = first(row, "OBJECT_ID", "INTLDES")
        name = row.get("OBJECT_NAME")

    elif source == "satnogs":
        n = row.get("norad_cat_id")
        c = row.get("cospar_id")
        name = row.get("name") if dataset == "satellites" else None

        sat_id = row.get("sat_id")

        if sat_id:
            aliases.append(("satnogs", str(sat_id)))

    elif source == "gcat":
        jcat = str(first(row, "JCAT", "#JCAT") or "").strip()

        if jcat:
            aliases.append(("gcat", jcat))

        # GCAT auxiliary components may share parent identifiers.
        # Only standard S catalogue entries establish cross-source identity.
        if jcat.startswith("S"):
            n = row.get("Satcat")
            c = row.get("Piece")

        name = row.get("Name")

    elif source == "launchlibrary" and dataset == "payloads":
        n = first(
            row,
            "norad_id",
            "norad_cat_id",
        )
        c = first(
            row,
            "cospar_id",
            "international_designator",
        )
        name = row.get("name")

        if row.get("id") is not None:
            aliases.append(
                (
                    "launchlibrary:payload",
                    str(row["id"]),
                )
            )

    return (
        norad(n),
        cospar(c),
        name,
        aliases,
    )


_PROPERTY_MAP = {
    "spacetrack": {
        "name": "object_name",
    },
    "celestrak": {
        "name": "OBJECT_NAME",
        "object_type": "OBJECT_TYPE",
        "country": "COUNTRY_CODE",
        "launch_date": "LAUNCH_DATE",
        "decay_date": "DECAY_DATE",
    },
    "gcat": {
        "name": "Name",
        "country": "State",
        "mass_kg": "Mass",
        "status": "Status",
    },
    "satnogs": {
        "name": "name",
        "status": "status",
    },
    "launchlibrary": {
        "name": "name",
    },
}


def properties(source, row):
    """Return a small canonical searchable projection.

    Provider-native fields remain preserved in ``source_records.data``.
    """
    result: dict[str, object] = {}

    for target, native_key in _PROPERTY_MAP.get(
        source,
        {},
    ).items():
        value = row.get(native_key)

        if value is None or value == "-":
            continue

        if target == "mass_kg":
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue

        elif target == "object_type":
            normalized = {
                "PAY": "payload",
                "R/B": "rocket_body",
                "DEB": "debris",
                "UNK": "unknown",
            }.get(str(value).strip().upper())

            if normalized is None:
                continue

            value = normalized

        elif target in {
            "launch_date",
            "decay_date",
        }:
            value = str(value).strip()

            if not value:
                continue

            try:
                value = date.fromisoformat(value[:10]).isoformat()
            except ValueError:
                continue

        result[target] = value

    return result


class IdentityStore:
    def __init__(self, con):
        self.con = con

    def resolve(
        self,
        source,
        dataset,
        row,
    ):
        n, c, name, aliases = claims(
            source,
            dataset,
            row,
        )

        identifiers = list(aliases)

        if n is not None:
            identifiers.append(("norad", str(n)))

        if c is not None:
            identifiers.append(("cospar", c))

        if not identifiers:
            return (
                None,
                "unidentified",
                "No explicit object identifier",
            )

        ids = set()

        for namespace, identifier in identifiers:
            found = self.con.execute(
                """
                SELECT object_id
                FROM object_identifiers
                WHERE namespace = ?
                  AND identifier = ?
                """,
                [namespace, identifier],
            ).fetchone()

            if found:
                ids.add(found[0])

        existing = [
            self.con.execute(
                """
                SELECT object_id,
                       norad_id,
                       cospar_id,
                       name
                FROM objects
                WHERE object_id = ?
                """,
                [oid],
            ).fetchone()
            for oid in sorted(ids)
        ]

        ns = {row[1] for row in existing if row[1] is not None}

        cs = {row[2] for row in existing if row[2] is not None}

        if n is not None:
            ns.add(n)

        if c is not None:
            cs.add(c)

        if len(ns) > 1 or len(cs) > 1:
            return (
                None,
                "conflict",
                "Incompatible NORAD/COSPAR claims",
            )

        if not existing:
            oid = str(uuid4())

            self.con.execute(
                """
                INSERT INTO objects(
                    object_id,
                    norad_id,
                    cospar_id,
                    name
                )
                VALUES (?, ?, ?, ?)
                """,
                [oid, n, c, name],
            )

        else:
            oid = existing[0][0]

            for other, _, _, _ in existing[1:]:
                for table in (
                    "source_records",
                    "object_properties",
                    "object_identifiers",
                    "object_redirects",
                ):
                    self.con.execute(
                        f"""
                        UPDATE {table}
                        SET object_id = ?
                        WHERE object_id = ?
                        """,
                        [oid, other],
                    )

                self.con.execute(
                    """
                    INSERT OR IGNORE INTO object_redirects
                    VALUES (?, ?)
                    """,
                    [other, oid],
                )

                self.con.execute(
                    """
                    DELETE FROM objects
                    WHERE object_id = ?
                    """,
                    [other],
                )

            self.con.execute(
                """
                UPDATE objects
                SET norad_id = ?,
                    cospar_id = ?,
                    name = coalesce(name, ?)
                WHERE object_id = ?
                """,
                [
                    next(iter(ns), None),
                    next(iter(cs), None),
                    name,
                    oid,
                ],
            )

        for namespace, identifier in identifiers:
            self.con.execute(
                """
                INSERT OR IGNORE INTO object_identifiers
                VALUES (?, ?, ?)
                """,
                [
                    namespace,
                    identifier,
                    oid,
                ],
            )

        return oid, "linked", None

    def _ingest_rows(
        self,
        records,
        artifact,
        *,
        first_row_index: int,
    ) -> int:
        count = 0

        for offset, row in enumerate(records):
            row_index = first_row_index + offset

            record_id = hashlib.sha256(
                (f"{artifact.artifact_id}:{row_index}").encode()
            ).hexdigest()

            exists = self.con.execute(
                """
                SELECT 1
                FROM source_records
                WHERE record_id = ?
                """,
                [record_id],
            ).fetchone()

            if exists:
                count += 1
                continue

            oid, status, detail = self.resolve(
                artifact.source,
                artifact.dataset,
                row,
            )

            self.con.execute(
                """
                INSERT INTO source_records
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    record_id,
                    artifact.artifact_id,
                    row_index,
                    artifact.source,
                    artifact.dataset,
                    oid,
                    artifact.retrieved_at,
                    dumps(row),
                    status,
                    detail,
                ],
            )

            if oid:
                props = [
                    (
                        record_id,
                        oid,
                        key,
                        dumps(value),
                    )
                    for key, value in properties(
                        artifact.source,
                        row,
                    ).items()
                ]

                if props:
                    self.con.executemany(
                        """
                        INSERT INTO object_properties
                        VALUES (?, ?, ?, ?)
                        """,
                        props,
                    )

            count += 1

        return count

    def ingest_batches(
        self,
        batches: Iterable[list[dict]],
        artifact,
        *,
        transaction: bool = True,
        commit_each_batch: bool = False,
        progress=None,
    ) -> int:
        """Ingest bounded batches.

        By default the complete ingestion is atomic.

        For large archived datasets, ``commit_each_batch=True`` bounds
        DuckDB transaction memory and makes reindexing resumable. Record
        IDs are deterministic per artifact/row, so already committed
        batches are safely skipped on a retry.
        """
        outer_transaction = transaction and not commit_each_batch

        if outer_transaction:
            self.con.execute("BEGIN TRANSACTION")

        row_index = 0
        batch_number = 0

        try:
            for batch in batches:
                if not batch:
                    continue

                batch_number += 1

                if transaction and commit_each_batch:
                    self.con.execute("BEGIN TRANSACTION")

                try:
                    processed = self._ingest_rows(
                        batch,
                        artifact,
                        first_row_index=row_index,
                    )

                    if transaction and commit_each_batch:
                        self.con.execute("COMMIT")

                except Exception:
                    if transaction and commit_each_batch:
                        self.con.execute("ROLLBACK")
                    raise

                row_index += processed

                if progress is not None:
                    progress(
                        row_index,
                        batch_number,
                    )

            if outer_transaction:
                self.con.execute("COMMIT")

        except Exception:
            if outer_transaction:
                self.con.execute("ROLLBACK")
            raise

        return row_index

    def ingest(
        self,
        records,
        artifact,
        *,
        transaction: bool = True,
    ) -> int:
        return self.ingest_batches(
            [records],
            artifact,
            transaction=transaction,
        )
