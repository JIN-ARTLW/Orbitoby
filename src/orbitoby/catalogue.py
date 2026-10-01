"""Local object lookup, search and raw-archive reindex APIs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from orbitoby.archive.raw import RawArtifact
from orbitoby.warehouse.identity import (
    IdentityStore,
    cospar,
    dumps,
    norad,
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)

    return digest.hexdigest()


class CatalogueAPI:
    def search(
        self,
        *,
        norad_id=None,
        cospar_id=None,
        name=None,
        source=None,
        dataset=None,
        properties=None,
        limit=100,
        offset=0,
    ):
        """Search locally indexed objects.

        Property filtering uses Orbitoby's canonical searchable projection.
        Provider-native values remain available in source-record data.
        """
        for key, value in (
            ("limit", limit),
            ("offset", offset),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{key} must be a nonnegative integer")

        where: list[str] = []
        values: list[object] = []

        for key, value, normalize in (
            ("norad_id", norad_id, norad),
            ("cospar_id", cospar_id, cospar),
        ):
            if value is None:
                continue

            normalized = normalize(value)

            if normalized is None:
                raise ValueError(f"Invalid {key}: {value!r}")

            where.append(f"o.{key} = ?")
            values.append(normalized)

        if name is not None:
            where.append(
                """
                (
                    contains(
                        lower(coalesce(o.name, '')),
                        lower(?)
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM object_properties p
                        WHERE p.object_id = o.object_id
                          AND p.property = 'name'
                          AND contains(
                              lower(
                                  json_extract_string(
                                      p.value,
                                      '$'
                                  )
                              ),
                              lower(?)
                          )
                    )
                )
                """
            )

            values.extend([name, name])

        if source is not None or dataset is not None:
            clause = """
                EXISTS (
                    SELECT 1
                    FROM source_records r
                    WHERE r.object_id = o.object_id
            """

            for key, value in (
                ("source", source),
                ("dataset", dataset),
            ):
                if value is not None:
                    clause += f" AND r.{key} = ?"
                    values.append(value)

            clause += ")"

            where.append(clause)

        for key, condition in (properties or {}).items():
            clause = """
                EXISTS (
                    SELECT 1
                    FROM object_properties p
                    WHERE p.object_id = o.object_id
                      AND p.property = ?
            """

            values.append(key)

            if isinstance(condition, tuple):
                if len(condition) != 2 or condition[0] not in (
                    "=",
                    "!=",
                    ">",
                    ">=",
                    "<",
                    "<=",
                ):
                    raise ValueError("Property comparison must be (operator, number)")

                op, value = condition

                if isinstance(value, bool) or not isinstance(
                    value,
                    (int, float),
                ):
                    raise TypeError("Comparison value must be numeric")

                dumps(value)

                clause += f" AND TRY_CAST(p.value AS DOUBLE) {op} ?"
                values.append(value)

            else:
                clause += " AND p.value = ?::JSON"
                values.append(dumps(condition))

            clause += ")"

            where.append(clause)

        query = """
            SELECT o.*
            FROM objects o
        """

        if where:
            query += " WHERE " + " AND ".join(where)

        query += """
            ORDER BY
                o.norad_id NULLS LAST,
                o.cospar_id NULLS LAST,
                o.object_id
            LIMIT ?
            OFFSET ?
        """

        return self.con.execute(
            query,
            values + [limit, offset],
        ).df()

    def object(
        self,
        *,
        norad_id=None,
        cospar_id=None,
        object_id=None,
    ):
        """Return identity and complete provider source records."""
        if norad_id is None and cospar_id is None and object_id is None:
            raise ValueError("Provide norad_id, cospar_id, or object_id")

        if object_id is not None:
            redirect = self.con.execute(
                """
                SELECT object_id
                FROM object_redirects
                WHERE old_object_id = ?
                """,
                [object_id],
            ).fetchone()

            if redirect:
                object_id = redirect[0]

            rows = self.con.execute(
                """
                SELECT *
                FROM objects
                WHERE object_id = ?
                """,
                [object_id],
            ).df()

            for key, value, normalize in (
                ("norad_id", norad_id, norad),
                ("cospar_id", cospar_id, cospar),
            ):
                if value is None:
                    continue

                normalized = normalize(value)

                if normalized is None:
                    raise ValueError(f"Invalid {key}")

                rows = rows[rows[key] == normalized]

        else:
            rows = self.search(
                norad_id=norad_id,
                cospar_id=cospar_id,
                limit=1,
            )

        if rows.empty:
            return None

        result = rows.astype(object).where(rows.notna(), None).iloc[0].to_dict()

        oid = result["object_id"]

        result["identifiers"] = (
            self.con.execute(
                """
                SELECT namespace, identifier
                FROM object_identifiers
                WHERE object_id = ?
                ORDER BY namespace, identifier
                """,
                [oid],
            )
            .df()
            .to_dict("records")
        )

        result["source_records"] = self.records(object_id=oid).to_dict("records")

        for record in result["source_records"]:
            record["data"] = json.loads(record["data"])

        props = (
            self.con.execute(
                """
                SELECT
                    p.property,
                    p.value,
                    r.source,
                    r.dataset,
                    r.retrieved_at,
                    p.record_id,
                    r.artifact_id
                FROM object_properties p
                JOIN source_records r
                  USING(record_id)
                WHERE p.object_id = ?
                ORDER BY
                    r.retrieved_at,
                    p.record_id,
                    p.property
                """,
                [oid],
            )
            .df()
            .to_dict("records")
        )

        for prop in props:
            prop["value"] = json.loads(prop["value"])

        result["properties"] = props

        return result

    def records(
        self,
        *,
        object_id=None,
        source=None,
        dataset=None,
        identity_status=None,
    ):
        """Inspect normalized provider records."""
        where: list[str] = []
        values: list[object] = []

        for key, value in (
            ("object_id", object_id),
            ("source", source),
            ("dataset", dataset),
            (
                "identity_status",
                identity_status,
            ),
        ):
            if value is not None:
                where.append(f"{key} = ?")
                values.append(value)

        query = """
            SELECT *
            FROM source_records
        """

        if where:
            query += " WHERE " + " AND ".join(where)

        query += """
            ORDER BY
                retrieved_at,
                artifact_id,
                row_index
        """

        return self.con.execute(
            query,
            values,
        ).df()

    def reindex(
        self,
        *,
        source=None,
        dataset=None,
        batch_size: int = 500,
        progress: bool = True,
    ):
        """Re-index archived raw files without downloading them again.

        Large archives are processed using bounded batches and bounded
        DuckDB transactions. Re-running an interrupted artifact is safe
        because source-record identifiers are deterministic.
        """
        import time

        import pandas as pd

        if batch_size <= 0:
            raise ValueError("batch_size must be > 0")

        # Bulk indexing does not depend on physical insertion order.
        # Lower parallelism also reduces peak DuckDB memory pressure.
        self.con.execute("SET preserve_insertion_order = false")
        self.con.execute("SET threads = 2")

        report = []

        artifacts = self.artifacts(
            source=source,
            dataset=dataset,
        ).sort_values("retrieved_at")

        for row in artifacts.to_dict("records"):
            started = time.monotonic()

            try:
                path = Path(row["path"])

                if _sha256_file(path) != row["sha256"]:
                    raise ValueError("Raw artifact checksum mismatch")

                adapter = self.get_source(row["source"])

                artifact = RawArtifact(
                    artifact_id=row["artifact_id"],
                    source=row["source"],
                    dataset=row["dataset"],
                    norad_id=row.get("norad_id"),
                    requested_start=row.get("requested_start"),
                    requested_end=row.get("requested_end"),
                    retrieved_at=row["retrieved_at"],
                    sha256=row["sha256"],
                    path=path,
                )

                batches = adapter.iter_normalized_file(
                    row["dataset"],
                    path,
                    batch_size=batch_size,
                )

                def show_progress(
                    rows_done,
                    batch_number,
                    *,
                    started_at=started,
                    source_name=row["source"],
                    dataset_name=row["dataset"],
                ):
                    if not progress:
                        return

                    elapsed = time.monotonic() - started_at

                    print(
                        (
                            f"\r[{source_name}/"
                            f"{dataset_name}] "
                            f"{rows_done:,} rows | "
                            f"{batch_number:,} batches | "
                            f"{elapsed:.1f} s"
                        ),
                        end="",
                        flush=True,
                    )

                count = IdentityStore(self.con).ingest_batches(
                    batches,
                    artifact,
                    commit_each_batch=True,
                    progress=show_progress,
                )

                elapsed = time.monotonic() - started

                if progress:
                    print(
                        (
                            f"\r[{row['source']}/"
                            f"{row['dataset']}] "
                            f"{count:,} rows indexed "
                            f"in {elapsed:.1f} s" + (" " * 20)
                        ),
                        flush=True,
                    )

                report.append(
                    (
                        row["artifact_id"],
                        "indexed",
                        count,
                        None,
                    )
                )

            except Exception as exc:  # noqa: BLE001 - per-artifact report
                if progress:
                    print()

                report.append(
                    (
                        row["artifact_id"],
                        "error",
                        0,
                        str(exc),
                    )
                )

        return pd.DataFrame(
            report,
            columns=[
                "artifact_id",
                "status",
                "rows",
                "error",
            ],
        )
