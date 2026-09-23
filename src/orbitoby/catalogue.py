"""Local object lookup, parameterized search, and raw-archive backfill APIs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from orbitoby.archive.raw import RawArtifact
from orbitoby.warehouse.identity import IdentityStore, cospar, dumps, norad


class CatalogueAPI:
    def search(self, *, norad_id=None, cospar_id=None, name=None, source=None,
               dataset=None, properties=None, limit=100, offset=0):
        """Search local objects. Filters combine with AND; properties match any
        preserved observation, including historical values. Numeric conditions
        use (operator, value), e.g. properties={"mass_kg": (">=", 100)}.
        """
        for key, value in (("limit", limit), ("offset", offset)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{key} must be a nonnegative integer")
        where, values = [], []
        for key, value, normalize in (("norad_id", norad_id, norad), ("cospar_id", cospar_id, cospar)):
            if value is not None:
                normalized = normalize(value)
                if normalized is None:
                    raise ValueError(f"Invalid {key}: {value!r}")
                where.append(f"o.{key}=?")
                values.append(normalized)
        if name is not None:
            # Literal, case-insensitive substring matching across source names.
            where.append("""(contains(lower(coalesce(o.name, '')), lower(?)) OR EXISTS (
                SELECT 1 FROM object_properties p WHERE p.object_id=o.object_id
                AND p.property IN ('name','Name','OBJECT_NAME','object_name','PLName')
                AND contains(lower(json_extract_string(p.value, '$')), lower(?))))""")
            values.extend([name, name])
        if source is not None or dataset is not None:
            clause = "EXISTS (SELECT 1 FROM source_records r WHERE r.object_id=o.object_id"
            for key, value in (("source", source), ("dataset", dataset)):
                if value is not None:
                    clause += f" AND r.{key}=?"
                    values.append(value)
            where.append(clause + ")")
        for key, condition in (properties or {}).items():
            clause = "EXISTS (SELECT 1 FROM object_properties p WHERE p.object_id=o.object_id AND p.property=?"
            values.append(key)
            if isinstance(condition, tuple):
                if len(condition) != 2 or condition[0] not in ("=", "!=", ">", ">=", "<", "<="):
                    raise ValueError("Property comparison must be (operator, number)")
                op, value = condition
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError("Comparison value must be numeric")
                dumps(value)  # reject NaN/infinity
                clause += f" AND TRY_CAST(p.value AS DOUBLE) {op} ?"
                values.append(value)
            else:
                clause += " AND p.value=?::JSON"
                values.append(dumps(condition))
            where.append(clause + ")")
        query = "SELECT o.* FROM objects o"
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY o.norad_id NULLS LAST, o.cospar_id NULLS LAST, o.object_id LIMIT ? OFFSET ?"
        return self.con.execute(query, values + [limit, offset]).df()

    def object(self, *, norad_id=None, cospar_id=None, object_id=None):
        """Return identity, identifiers, source records and property observations.

        Returns None when absent. Multiple supplied identifiers must all match.
        Performs no network requests and does not select a 'winning' property.
        """
        if norad_id is None and cospar_id is None and object_id is None:
            raise ValueError("Provide norad_id, cospar_id, or object_id")
        if object_id is not None:
            redirect = self.con.execute("SELECT object_id FROM object_redirects WHERE old_object_id=?", [object_id]).fetchone()
            if redirect:
                object_id = redirect[0]
            rows = self.con.execute("SELECT * FROM objects WHERE object_id=?", [object_id]).df()
            # Validate additional filters even when the object does not exist.
            for key, value, normalize in (("norad_id", norad_id, norad), ("cospar_id", cospar_id, cospar)):
                if value is not None:
                    normalized = normalize(value)
                    if normalized is None:
                        raise ValueError(f"Invalid {key}")
                    rows = rows[rows[key] == normalized]
        else:
            rows = self.search(norad_id=norad_id, cospar_id=cospar_id, limit=1)
        if rows.empty:
            return None
        result = rows.astype(object).where(rows.notna(), None).iloc[0].to_dict()
        oid = result["object_id"]
        result["identifiers"] = self.con.execute(
            "SELECT namespace, identifier FROM object_identifiers WHERE object_id=? ORDER BY namespace, identifier", [oid]
        ).df().to_dict("records")
        result["source_records"] = self.records(object_id=oid).to_dict("records")
        for record in result["source_records"]:
            record["data"] = json.loads(record["data"])
        props = self.con.execute("""
            SELECT p.property, p.value, r.source, r.dataset, r.retrieved_at,
                   p.record_id, r.artifact_id
            FROM object_properties p JOIN source_records r USING(record_id)
            WHERE p.object_id=? ORDER BY r.retrieved_at, p.record_id, p.property
        """, [oid]).df().to_dict("records")
        for prop in props:
            prop["value"] = json.loads(prop["value"])
        result["properties"] = props
        return result

    def records(self, *, object_id=None, source=None, dataset=None, identity_status=None):
        """Inspect normalized records, including weather and unresolved claims."""
        where, values = [], []
        for key, value in (("object_id", object_id), ("source", source),
                           ("dataset", dataset), ("identity_status", identity_status)):
            if value is not None:
                where.append(f"{key}=?")
                values.append(value)
        query = "SELECT * FROM source_records"
        if where:
            query += " WHERE " + " AND ".join(where)
        return self.con.execute(query + " ORDER BY retrieved_at, artifact_id, row_index", values).df()

    def reindex(self, *, source=None, dataset=None):
        """Index previously archived raw files without downloading them again.

        Idempotent per artifact and row. Returns an artifact-level report and
        continues past missing/corrupt files. Local display limits are ignored.
        """
        import pandas as pd
        report = []
        artifacts = self.artifacts(source=source, dataset=dataset).sort_values("retrieved_at")
        for row in artifacts.to_dict("records"):
            try:
                payload = Path(row["path"]).read_bytes()
                if hashlib.sha256(payload).hexdigest() != row["sha256"]:
                    raise ValueError("Raw artifact checksum mismatch")
                records = self.get_source(row["source"]).normalize(row["dataset"], payload)
                artifact = RawArtifact(
                    artifact_id=row["artifact_id"], source=row["source"], dataset=row["dataset"],
                    norad_id=None, requested_start=None, requested_end=None,
                    retrieved_at=row["retrieved_at"], sha256=row["sha256"], path=Path(row["path"]),
                )
                IdentityStore(self.con).ingest(records, artifact)
                report.append((row["artifact_id"], "indexed", len(records), None))
            except Exception as exc:
                report.append((row["artifact_id"], "error", 0, str(exc)))
        return pd.DataFrame(report, columns=["artifact_id", "status", "rows", "error"])
