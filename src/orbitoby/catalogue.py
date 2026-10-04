"""Local object lookup, search and raw-archive reindex APIs."""

from __future__ import annotations

import hashlib
import json
from datetime import date
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
    def objects(
        self,
        *,
        search: str | None = None,
        norad_id=None,
        cospar_id=None,
        source: str | None = None,
        dataset: str | None = None,
        properties=None,
        start=None,
        end=None,
        existence: str = "overlap",
        object_type: str | None = None,
        sync: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ):
        """Search locally indexed space objects.

        Simple discovery remains local-only by default.

        Providing ``start`` and ``end`` enables a
        period-aware population query using the latest
        locally indexed CelesTrak SATCAT assertion.

        ``sync=True`` refreshes the complete CelesTrak
        SATCAT before the query.

        Period semantics are date-granularity and the
        requested research interval is [start, end).

        ``existence="overlap"``:
            object existed during at least part of the
            requested interval.

        ``existence="throughout"``:
            object existed throughout the requested
            interval.

        Provider-native source rows remain preserved.
        """

        if search is not None:
            if not isinstance(search, str):
                raise TypeError("search must be a string or None")

            search = search.strip()

            if not search:
                raise ValueError("search must not be empty")

        if isinstance(sync, bool) is False:
            raise TypeError("sync must be a boolean")

        if sync:
            self.fetch(
                source="celestrak",
                dataset="satcat",
                all=True,
            )

        temporal = start is not None or end is not None or object_type is not None

        if not temporal:
            local_limit = 100 if limit is None else limit
            if source is not None:
                adapter = self.get_source(source)

                if dataset is not None:
                    if dataset not in adapter.datasets:
                        available = ", ".join(adapter.datasets)

                        raise ValueError(
                            f"Unknown dataset "
                            f"{dataset!r} for "
                            f"source {source!r}. "
                            f"Available datasets: "
                            f"{available}"
                        )

                    if not (adapter.should_index_identity(dataset)):
                        raise ValueError(
                            f"{source!r}/"
                            f"{dataset!r} is not "
                            "an object-catalogue "
                            "dataset."
                        )

            return self.search(
                norad_id=norad_id,
                cospar_id=cospar_id,
                name=search,
                source=source,
                dataset=dataset,
                properties=properties,
                limit=local_limit,
                offset=offset,
            )

        if (start is None) != (end is None):
            raise ValueError("start and end must be provided together")

        if start is None:
            raise ValueError(
                "start and end are required for period-aware object discovery"
            )

        def parse_date(
            value,
            *,
            name,
        ):
            if isinstance(value, date):
                return value

            if not isinstance(value, str):
                raise TypeError(f"{name} must be an ISO date string or date")

            try:
                return date.fromisoformat(value.strip())
            except ValueError as exc:
                raise ValueError(f"Invalid {name}: {value!r}") from exc

        start_date = parse_date(
            start,
            name="start",
        )
        end_date = parse_date(
            end,
            name="end",
        )

        if start_date >= end_date:
            raise ValueError("start must be before end")

        if existence not in {
            "overlap",
            "throughout",
        }:
            raise ValueError("existence must be 'overlap' or 'throughout'")

        if source not in {
            None,
            "celestrak",
        }:
            raise ValueError(
                "Period-aware object discovery "
                "currently uses the CelesTrak "
                "SATCAT population source."
            )

        if dataset not in {
            None,
            "satcat",
        }:
            raise ValueError(
                "Period-aware object discovery currently uses dataset='satcat'."
            )

        canonical_type = None

        if object_type is not None:
            if not isinstance(
                object_type,
                str,
            ):
                raise TypeError("object_type must be a string")

            key = object_type.strip().lower().replace("-", "_").replace(" ", "_")

            aliases = {
                "pay": "payload",
                "payload": "payload",
                "satellite": "payload",
                "r/b": "rocket_body",
                "rocket_body": "rocket_body",
                "rocketbody": "rocket_body",
                "deb": "debris",
                "debris": "debris",
                "unk": "unknown",
                "unknown": "unknown",
            }

            try:
                canonical_type = aliases[key]
            except KeyError as exc:
                raise ValueError(
                    "object_type must be one of "
                    "payload, rocket_body, debris, "
                    "or unknown"
                ) from exc

        for key, value in (
            ("limit", limit),
            ("offset", offset),
        ):
            if key == "limit" and value is None:
                continue

            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{key} must be a nonnegative integer")

        where = []
        values = []

        if search is not None:
            where.append("contains(lower(coalesce(x.name, '')), lower(?))")
            values.append(search)

        if norad_id is not None:
            normalized = norad(norad_id)

            if normalized is None:
                raise ValueError(f"Invalid norad_id: {norad_id!r}")

            where.append("x.norad_id = ?")
            values.append(normalized)

        if cospar_id is not None:
            normalized = cospar(cospar_id)

            if normalized is None:
                raise ValueError(f"Invalid cospar_id: {cospar_id!r}")

            where.append("x.cospar_id = ?")
            values.append(normalized)

        if canonical_type is not None:
            where.append("x.object_type = ?")
            values.append(canonical_type)

        if existence == "overlap":
            where.extend(
                [
                    "x.launch_date IS NOT NULL",
                    "x.launch_date < ?",
                    "(x.decay_date IS NULL OR x.decay_date >= ?)",
                ]
            )
            values.extend(
                [
                    end_date,
                    start_date,
                ]
            )

        else:
            where.extend(
                [
                    "x.launch_date IS NOT NULL",
                    "x.launch_date <= ?",
                    "(x.decay_date IS NULL OR x.decay_date >= ?)",
                ]
            )
            values.extend(
                [
                    start_date,
                    end_date,
                ]
            )

        # _orbitoby_period_snapshot_fast_path
        #
        # A complete CelesTrak SATCAT snapshot is population data.
        # Do not force tens of thousands of rows through the generic
        # row-by-row identity store merely to answer a period query.
        #
        # If a local raw SATCAT CSV exists, query that snapshot
        # directly. Generic identity SQL remains the fallback.
        if (
            not properties
            and hasattr(
                self,
                "artifacts",
            )
            and hasattr(
                self,
                "get_source",
            )
        ):
            artifact_rows = self.artifacts(
                source="celestrak",
                dataset="satcat",
            )

            if not artifact_rows.empty:
                latest_artifact = artifact_rows.iloc[0]

                artifact_path = Path(latest_artifact["path"])

                if artifact_path.exists() and artifact_path.suffix.lower() == ".csv":
                    import pandas as pd

                    adapter = self.get_source("celestrak")

                    records = adapter.normalize(
                        "satcat",
                        artifact_path.read_bytes(),
                        all=True,
                    )

                    population = pd.DataFrame(records)

                    required_columns = {
                        "NORAD_CAT_ID",
                        "OBJECT_NAME",
                        "OBJECT_TYPE",
                        "LAUNCH_DATE",
                        "DECAY_DATE",
                    }

                    missing_columns = required_columns - set(population.columns)

                    if missing_columns:
                        raise ValueError(
                            "CelesTrak SATCAT "
                            "snapshot is missing "
                            "required columns: " + ", ".join(sorted(missing_columns))
                        )

                    population["norad_id"] = population["NORAD_CAT_ID"].map(norad)

                    if "OBJECT_ID" in population.columns:
                        population["cospar_id"] = population["OBJECT_ID"].map(cospar)
                    else:
                        population["cospar_id"] = None

                    population["name"] = population["OBJECT_NAME"]

                    object_type_map = {
                        "PAY": "payload",
                        "R/B": "rocket_body",
                        "DEB": "debris",
                        "UNK": "unknown",
                    }

                    population["object_type"] = (
                        population["OBJECT_TYPE"]
                        .astype(str)
                        .str.strip()
                        .str.upper()
                        .map(object_type_map)
                    )

                    population["launch_date"] = pd.to_datetime(
                        population["LAUNCH_DATE"],
                        errors="coerce",
                    ).dt.date

                    population["decay_date"] = pd.to_datetime(
                        population["DECAY_DATE"],
                        errors="coerce",
                    ).dt.date

                    population["catalogue_source"] = "celestrak"

                    population["catalogue_retrieved_at"] = latest_artifact[
                        "retrieved_at"
                    ]

                    population["catalogue_artifact_id"] = latest_artifact["artifact_id"]

                    launch_ts = pd.to_datetime(
                        population["launch_date"],
                        errors="coerce",
                    )

                    decay_ts = pd.to_datetime(
                        population["decay_date"],
                        errors="coerce",
                    )

                    start_ts = pd.Timestamp(start_date)

                    end_ts = pd.Timestamp(end_date)

                    mask = launch_ts.notna()

                    if existence == "overlap":
                        mask &= launch_ts < end_ts

                        mask &= decay_ts.isna() | (decay_ts >= start_ts)

                    else:
                        mask &= launch_ts <= start_ts

                        mask &= population["decay_date"].isna() | (decay_ts >= end_ts)

                    if canonical_type is not None:
                        mask &= population["object_type"] == canonical_type

                    if search is not None:
                        mask &= (
                            population["name"]
                            .fillna("")
                            .astype(str)
                            .str.contains(
                                search,
                                case=False,
                                regex=False,
                            )
                        )

                    if norad_id is not None:
                        target_norad = norad(norad_id)

                        if target_norad is None:
                            raise ValueError(f"Invalid norad_id: {norad_id!r}")

                        mask &= population["norad_id"] == target_norad

                    if cospar_id is not None:
                        target_cospar = cospar(cospar_id)

                        if target_cospar is None:
                            raise ValueError(f"Invalid cospar_id: {cospar_id!r}")

                        mask &= population["cospar_id"] == target_cospar

                    result = (
                        population.loc[
                            mask,
                            [
                                "norad_id",
                                "cospar_id",
                                "name",
                                "object_type",
                                "launch_date",
                                "decay_date",
                                "catalogue_source",
                                "catalogue_retrieved_at",
                                "catalogue_artifact_id",
                            ],
                        ]
                        .sort_values(
                            [
                                "norad_id",
                                "cospar_id",
                            ],
                            kind="stable",
                            na_position="last",
                        )
                        .reset_index(drop=True)
                    )

                    if offset:
                        result = result.iloc[offset:]

                    if limit is not None:
                        result = result.iloc[:limit]

                    return result.reset_index(drop=True)

        for key, condition in (properties or {}).items():
            clause = """
                EXISTS (
                    SELECT 1
                    FROM object_properties p
                    WHERE p.object_id =
                          x.object_id
                      AND p.property = ?
            """

            values.append(key)

            if isinstance(
                condition,
                tuple,
            ):
                if len(condition) != 2 or condition[0] not in {
                    "=",
                    "!=",
                    ">",
                    ">=",
                    "<",
                    "<=",
                }:
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

        effective_limit = 9223372036854775807 if limit is None else limit

        query = """
            WITH latest_satcat AS (
                SELECT
                    object_id,
                    data,
                    retrieved_at,
                    artifact_id,
                    record_id,
                    row_number() OVER (
                        PARTITION BY object_id
                        ORDER BY
                            retrieved_at DESC,
                            record_id DESC
                    ) AS rn
                FROM source_records
                WHERE source = 'celestrak'
                  AND dataset = 'satcat'
                  AND identity_status = 'linked'
            ),
            population AS (
                SELECT
                    o.object_id,
                    o.norad_id,
                    o.cospar_id,
                    o.name,
                    CASE
                        WHEN upper(
                            json_extract_string(
                                r.data,
                                '$.OBJECT_TYPE'
                            )
                        ) = 'PAY'
                            THEN 'payload'
                        WHEN upper(
                            json_extract_string(
                                r.data,
                                '$.OBJECT_TYPE'
                            )
                        ) = 'R/B'
                            THEN 'rocket_body'
                        WHEN upper(
                            json_extract_string(
                                r.data,
                                '$.OBJECT_TYPE'
                            )
                        ) = 'DEB'
                            THEN 'debris'
                        WHEN upper(
                            json_extract_string(
                                r.data,
                                '$.OBJECT_TYPE'
                            )
                        ) = 'UNK'
                            THEN 'unknown'
                        ELSE NULL
                    END AS object_type,
                    TRY_CAST(
                        substr(
                            json_extract_string(
                                r.data,
                                '$.LAUNCH_DATE'
                            ),
                            1,
                            10
                        )
                        AS DATE
                    ) AS launch_date,
                    TRY_CAST(
                        substr(
                            json_extract_string(
                                r.data,
                                '$.DECAY_DATE'
                            ),
                            1,
                            10
                        )
                        AS DATE
                    ) AS decay_date,
                    r.retrieved_at
                        AS catalogue_retrieved_at,
                    r.artifact_id
                        AS catalogue_artifact_id,
                    'celestrak'
                        AS catalogue_source
                FROM objects o
                JOIN latest_satcat r
                  ON r.object_id = o.object_id
                 AND r.rn = 1
            )
            SELECT *
            FROM population x
        """

        if where:
            query += " WHERE " + " AND ".join(where)

        query += """
            ORDER BY
                x.norad_id NULLS LAST,
                x.cospar_id NULLS LAST,
                x.object_id
            LIMIT ?
            OFFSET ?
        """

        return self.con.execute(
            query,
            values
            + [
                effective_limit,
                offset,
            ],
        ).df()

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
