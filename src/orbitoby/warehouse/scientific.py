from __future__ import annotations

import base64
import hashlib
import json
import math
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import duckdb
import pandas as pd

from orbitoby.config import CANONICAL_DIR

SCHEMA_VERSION = "canonical-store-v1"
COVERAGE_SCHEMA_VERSION = "scientific-coverage-v1"

SCHEMA = """
CREATE TABLE IF NOT EXISTS scientific_files (
    store_id VARCHAR PRIMARY KEY,

    source VARCHAR NOT NULL,
    dataset VARCHAR NOT NULL,
    metric VARCHAR NOT NULL,

    artifact_id VARCHAR NOT NULL,
    raw_sha256 VARCHAR NOT NULL,

    artifact_kind VARCHAR NOT NULL,
    method VARCHAR,

    transform VARCHAR NOT NULL,
    transform_version VARCHAR NOT NULL,

    requested_start TIMESTAMPTZ NOT NULL,
    requested_end TIMESTAMPTZ NOT NULL,

    observed_start TIMESTAMPTZ NOT NULL,
    observed_end TIMESTAMPTZ NOT NULL,

    row_count BIGINT NOT NULL,

    logical_sha256 VARCHAR NOT NULL,
    parquet_sha256 VARCHAR NOT NULL,

    path VARCHAR NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS scientific_lookup
ON scientific_files (
    metric,
    source,
    dataset,
    requested_start,
    requested_end
);

CREATE TABLE IF NOT EXISTS scientific_coverage (
    coverage_id VARCHAR PRIMARY KEY,

    source VARCHAR NOT NULL,
    dataset VARCHAR NOT NULL,
    metric VARCHAR NOT NULL,

    artifact_id VARCHAR NOT NULL,
    raw_sha256 VARCHAR NOT NULL,

    transform VARCHAR NOT NULL,
    transform_version VARCHAR NOT NULL,

    requested_start TIMESTAMPTZ NOT NULL,
    requested_end TIMESTAMPTZ NOT NULL,

    row_count BIGINT NOT NULL,
    store_id VARCHAR,

    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS scientific_coverage_lookup
ON scientific_coverage (
    metric,
    source,
    dataset,
    transform,
    transform_version,
    requested_start,
    requested_end
);
"""


CANONICAL_COLUMNS = (
    "timestamp",
    "metric",
    "value",
    "unit",
    "source_value",
    "is_missing",
    "missing_reason",
    "source",
    "dataset",
    "source_field",
    "source_version",
    "status",
    "provider_status",
    "quality_flag",
    "artifact_kind",
    "method",
    "interval_start",
    "interval_end",
    "artifact_id",
    "retrieved_at",
    "transform",
    "transform_version",
    "context",
)


DISK_COLUMNS = (
    "timestamp",
    "metric",
    "value",
    "unit",
    "source_value_json",
    "is_missing",
    "missing_reason",
    "source",
    "dataset",
    "source_field",
    "source_version",
    "status",
    "provider_status_json",
    "quality_flag_json",
    "artifact_kind",
    "method",
    "interval_start",
    "interval_end",
    "artifact_id",
    "retrieved_at",
    "transform",
    "transform_version",
    "context_json",
)


@dataclass(frozen=True, slots=True)
class ScientificFile:
    store_id: str
    source: str
    dataset: str
    metric: str

    artifact_id: str
    raw_sha256: str

    artifact_kind: str
    method: str | None

    transform: str
    transform_version: str

    requested_start: datetime
    requested_end: datetime

    observed_start: datetime
    observed_end: datetime

    row_count: int

    logical_sha256: str
    parquet_sha256: str

    path: Path
    created_at: datetime


class ScientificStore:
    """Immutable provenance-rich canonical scientific storage."""

    def __init__(
        self,
        con: duckdb.DuckDBPyConnection,
        *,
        root: str | Path | None = None,
    ) -> None:
        self.con = con

        self.con.execute("SET TimeZone = 'UTC'")

        self.root = (
            Path(root if root is not None else CANONICAL_DIR).expanduser().resolve()
        )

        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.con.execute(SCHEMA)

    @staticmethod
    def _utc_timestamp(
        value: Any,
        *,
        name: str,
    ) -> pd.Timestamp:
        try:
            result = pd.Timestamp(value)
        except Exception as exc:
            raise ValueError(f"{name} is not a valid date/time.") from exc

        if result.tzinfo is None:
            return result.tz_localize("UTC")

        return result.tz_convert("UTC")

    @staticmethod
    def _required_columns(
        frame: pd.DataFrame,
    ) -> None:
        missing = set(CANONICAL_COLUMNS) - set(frame.columns)

        if missing:
            raise ValueError(
                "Canonical frame is missing columns: " + ", ".join(sorted(missing))
            )

    @staticmethod
    def _is_null_scalar(
        value: Any,
    ) -> bool:
        if value is None or value is pd.NA or value is pd.NaT:
            return True

        try:
            result = pd.isna(value)
        except (TypeError, ValueError):
            return False

        try:
            return bool(result)
        except (TypeError, ValueError):
            return False

    @classmethod
    def _single_value(
        cls,
        frame: pd.DataFrame,
        column: str,
        *,
        allow_none: bool,
    ) -> Any:
        values = []

        for value in frame[column].tolist():
            normalized = None if cls._is_null_scalar(value) else value

            if normalized not in values:
                values.append(normalized)

        if len(values) != 1:
            raise ValueError(
                f"Canonical column {column!r} "
                "must contain exactly one value "
                "per stored file."
            )

        value = values[0]

        if value is None and not allow_none:
            raise ValueError(f"Canonical column {column!r} must not be null.")

        return value

    @staticmethod
    def _jsonable(
        value: Any,
    ) -> Any:
        if value is None or value is pd.NA or value is pd.NaT:
            return None

        if isinstance(value, dict):
            return {
                str(key): ScientificStore._jsonable(item) for key, item in value.items()
            }

        if isinstance(
            value,
            (
                list,
                tuple,
            ),
        ):
            return [ScientificStore._jsonable(item) for item in value]

        if isinstance(value, bytes):
            return {"__orbitoby_bytes__": (base64.b64encode(value).decode("ascii"))}

        if isinstance(value, pd.Timestamp):
            return {"__orbitoby_datetime__": value.isoformat()}

        if isinstance(value, datetime):
            return {"__orbitoby_datetime__": value.isoformat()}

        if isinstance(value, date):
            return {"__orbitoby_date__": value.isoformat()}

        if hasattr(value, "item"):
            try:
                value = value.item()
            except ValueError:
                pass

        if isinstance(value, float):
            if math.isnan(value):
                return {
                    "__orbitoby_float__": "nan",
                }

            if math.isinf(value):
                return {
                    "__orbitoby_float__": ("inf" if value > 0 else "-inf"),
                }

        if isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
            ),
        ):
            return value

        raise TypeError(
            "Canonical provenance value is not JSON-serializable: "
            f"{type(value).__name__}"
        )

    @staticmethod
    def _restore_jsonable(
        value: Any,
    ) -> Any:
        if isinstance(value, list):
            return [ScientificStore._restore_jsonable(item) for item in value]

        if not isinstance(value, dict):
            return value

        if set(value) == {"__orbitoby_bytes__"}:
            return base64.b64decode(value["__orbitoby_bytes__"])

        if set(value) == {"__orbitoby_datetime__"}:
            return pd.Timestamp(value["__orbitoby_datetime__"]).to_pydatetime()

        if set(value) == {"__orbitoby_date__"}:
            return date.fromisoformat(value["__orbitoby_date__"])

        if set(value) == {"__orbitoby_float__"}:
            marker = value["__orbitoby_float__"]

            if marker == "nan":
                return float("nan")

            if marker == "inf":
                return float("inf")

            if marker == "-inf":
                return float("-inf")

            raise ValueError(f"Unknown serialized float marker: {marker!r}")

        return {
            key: ScientificStore._restore_jsonable(item) for key, item in value.items()
        }

    @classmethod
    def _json_dumps(
        cls,
        value: Any,
    ) -> str:
        return json.dumps(
            cls._jsonable(value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    @classmethod
    def _json_loads(
        cls,
        value: str,
    ) -> Any:
        return cls._restore_jsonable(json.loads(value))

    @classmethod
    def _nullable_string(
        cls,
        series: pd.Series,
    ) -> pd.Series:
        return series.map(
            lambda value: pd.NA if cls._is_null_scalar(value) else str(value)
        ).astype("string")

    @classmethod
    def _disk_frame(
        cls,
        frame: pd.DataFrame,
    ) -> pd.DataFrame:
        result = frame.loc[
            :,
            list(CANONICAL_COLUMNS),
        ].copy()

        result["timestamp"] = pd.to_datetime(
            result["timestamp"],
            utc=True,
            errors="raise",
        )

        for column in (
            "interval_start",
            "interval_end",
            "retrieved_at",
        ):
            result[column] = pd.to_datetime(
                result[column],
                utc=True,
                errors="raise",
            )

        result["value"] = pd.to_numeric(
            result["value"],
            errors="raise",
        ).astype("Float64")

        result["is_missing"] = result["is_missing"].astype("boolean")

        if result["is_missing"].isna().any():
            raise ValueError("is_missing must not contain null values.")

        for column in (
            "metric",
            "unit",
            "missing_reason",
            "source",
            "dataset",
            "source_field",
            "source_version",
            "status",
            "artifact_kind",
            "method",
            "artifact_id",
            "transform",
            "transform_version",
        ):
            result[column] = cls._nullable_string(result[column])

        result["source_value_json"] = result["source_value"].map(cls._json_dumps)

        result["provider_status_json"] = result["provider_status"].map(cls._json_dumps)

        result["quality_flag_json"] = result["quality_flag"].map(cls._json_dumps)

        result["context_json"] = result["context"].map(cls._json_dumps)

        result = result.drop(
            columns=[
                "source_value",
                "provider_status",
                "quality_flag",
                "context",
            ]
        )

        return result.loc[
            :,
            list(DISK_COLUMNS),
        ]

    @classmethod
    def _memory_frame(
        cls,
        frame: pd.DataFrame,
    ) -> pd.DataFrame:
        result = frame.copy()

        result["source_value"] = result["source_value_json"].map(cls._json_loads)

        result["provider_status"] = result["provider_status_json"].map(cls._json_loads)

        result["quality_flag"] = result["quality_flag_json"].map(cls._json_loads)

        result["context"] = result["context_json"].map(cls._json_loads)

        result = result.drop(
            columns=[
                "source_value_json",
                "provider_status_json",
                "quality_flag_json",
                "context_json",
            ]
        )

        result["timestamp"] = pd.to_datetime(
            result["timestamp"],
            utc=True,
        )

        for column in (
            "interval_start",
            "interval_end",
            "retrieved_at",
        ):
            result[column] = pd.to_datetime(
                result[column],
                utc=True,
            )

        return result.loc[
            :,
            list(CANONICAL_COLUMNS),
        ]

    @classmethod
    def _digest_scalar(
        cls,
        value: Any,
    ) -> Any:
        if cls._is_null_scalar(value):
            return None

        if isinstance(value, pd.Timestamp):
            timestamp = value

            if timestamp.tzinfo is None:
                timestamp = timestamp.tz_localize("UTC")
            else:
                timestamp = timestamp.tz_convert("UTC")

            return timestamp.isoformat()

        if isinstance(value, datetime):
            timestamp = pd.Timestamp(value)

            if timestamp.tzinfo is None:
                timestamp = timestamp.tz_localize("UTC")
            else:
                timestamp = timestamp.tz_convert("UTC")

            return timestamp.isoformat()

        if hasattr(value, "item"):
            try:
                value = value.item()
            except ValueError:
                pass

        if isinstance(value, float) and math.isinf(value):
            return "__inf__" if value > 0 else "__-inf__"

        return value

    @classmethod
    def _logical_sha256(
        cls,
        frame: pd.DataFrame,
    ) -> str:
        digest = hashlib.sha256()

        for row in frame.itertuples(
            index=False,
            name=None,
        ):
            encoded = {
                column: cls._digest_scalar(value)
                for column, value in zip(
                    frame.columns,
                    row,
                    strict=True,
                )
            }

            digest.update(
                json.dumps(
                    encoded,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")
            )
            digest.update(b"\n")

        return digest.hexdigest()

    @staticmethod
    def _file_sha256(
        path: Path,
    ) -> str:
        digest = hashlib.sha256()

        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)

                if not chunk:
                    break

                digest.update(chunk)

        return digest.hexdigest()

    @staticmethod
    def _sql_path(
        path: Path,
    ) -> str:
        return str(path).replace(
            "'",
            "''",
        )

    def _write_parquet(
        self,
        frame: pd.DataFrame,
        path: Path,
    ) -> None:
        con = duckdb.connect()

        con.execute("SET TimeZone = 'UTC'")

        try:
            con.register(
                "_orbitoby_canonical",
                frame,
            )

            target = self._sql_path(path)

            con.execute(
                f"""
                COPY _orbitoby_canonical
                TO '{target}'
                (
                    FORMAT PARQUET,
                    COMPRESSION ZSTD
                )
                """
            )
        finally:
            con.close()

    def _read_parquet_disk(
        self,
        path: Path,
    ) -> pd.DataFrame:
        con = duckdb.connect()

        con.execute("SET TimeZone = 'UTC'")

        try:
            target = self._sql_path(path)

            return con.execute(
                f"""
                SELECT *
                FROM read_parquet(
                    '{target}',
                    hive_partitioning = false
                )
                """
            ).df()
        finally:
            con.close()

    def _validate_parquet(
        self,
        path: Path,
        *,
        expected_rows: int,
        expected_logical_sha256: str,
    ) -> None:
        persisted = self._read_parquet_disk(path)

        if tuple(persisted.columns) != DISK_COLUMNS:
            raise RuntimeError("Canonical Parquet schema mismatch.")

        if len(persisted) != expected_rows:
            raise RuntimeError("Canonical Parquet row-count mismatch.")

        actual = self._logical_sha256(persisted)

        if actual != expected_logical_sha256:
            raise RuntimeError("Canonical Parquet read-back validation failed.")

    def _artifact_provenance(
        self,
        *,
        artifact_id: str,
        source: str,
        dataset: str,
    ) -> str:
        row = self.con.execute(
            """
            SELECT source, dataset, sha256
            FROM artifacts
            WHERE artifact_id = ?
            """,
            [artifact_id],
        ).fetchone()

        if row is None:
            raise ValueError("Canonical data references an unregistered raw artifact.")

        raw_source, raw_dataset, raw_sha256 = row

        if raw_source != source:
            raise ValueError("Canonical source does not match raw artifact source.")

        if raw_dataset != dataset:
            raise ValueError("Canonical dataset does not match raw artifact dataset.")

        return str(raw_sha256)

    @staticmethod
    def _partition_component(
        value: str,
    ) -> str:
        return quote(
            value,
            safe="-_.",
        )

    def _relative_path(
        self,
        *,
        source: str,
        dataset: str,
        metric: str,
        year: int,
        store_id: str,
    ) -> Path:
        return (
            Path("source=" + self._partition_component(source))
            / ("dataset=" + self._partition_component(dataset))
            / ("metric=" + self._partition_component(metric))
            / f"year={year:04d}"
            / f"{store_id}.parquet"
        )

    def _record(
        self,
        store_id: str,
    ) -> ScientificFile | None:
        row = self.con.execute(
            """
            SELECT
                store_id,
                source,
                dataset,
                metric,
                artifact_id,
                raw_sha256,
                artifact_kind,
                method,
                transform,
                transform_version,
                requested_start,
                requested_end,
                observed_start,
                observed_end,
                row_count,
                logical_sha256,
                parquet_sha256,
                path,
                created_at
            FROM scientific_files
            WHERE store_id = ?
            """,
            [store_id],
        ).fetchone()

        if row is None:
            return None

        return ScientificFile(
            store_id=row[0],
            source=row[1],
            dataset=row[2],
            metric=row[3],
            artifact_id=row[4],
            raw_sha256=row[5],
            artifact_kind=row[6],
            method=row[7],
            transform=row[8],
            transform_version=row[9],
            requested_start=row[10],
            requested_end=row[11],
            observed_start=row[12],
            observed_end=row[13],
            row_count=row[14],
            logical_sha256=row[15],
            parquet_sha256=row[16],
            path=self.root / row[17],
            created_at=row[18],
        )

    def _verify_record(
        self,
        record: ScientificFile,
    ) -> None:
        resolved = record.path.resolve()

        if not resolved.is_relative_to(self.root):
            raise RuntimeError("Scientific file path escapes canonical storage root.")

        if not resolved.is_file():
            raise RuntimeError("Scientific Parquet file is missing.")

        actual_sha256 = self._file_sha256(resolved)

        if actual_sha256 != record.parquet_sha256:
            raise RuntimeError("Scientific Parquet checksum mismatch.")

        self._validate_parquet(
            resolved,
            expected_rows=record.row_count,
            expected_logical_sha256=(record.logical_sha256),
        )

    def write(
        self,
        frame: pd.DataFrame,
        *,
        requested_start: Any,
        requested_end: Any,
    ) -> ScientificFile:
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("frame must be a pandas DataFrame.")

        if frame.empty:
            raise ValueError("Cannot persist an empty canonical frame.")

        self._required_columns(frame)

        start = self._utc_timestamp(
            requested_start,
            name="requested_start",
        )
        end = self._utc_timestamp(
            requested_end,
            name="requested_end",
        )

        if start >= end:
            raise ValueError("requested_start must be before requested_end.")

        working = frame.loc[
            :,
            list(CANONICAL_COLUMNS),
        ].copy()

        working["timestamp"] = pd.to_datetime(
            working["timestamp"],
            utc=True,
            errors="raise",
        )

        outside = (working["timestamp"] < start) | (working["timestamp"] >= end)

        if outside.any():
            raise ValueError(
                "Canonical frame contains rows outside requested [start, end)."
            )

        source = str(
            self._single_value(
                working,
                "source",
                allow_none=False,
            )
        )

        dataset = str(
            self._single_value(
                working,
                "dataset",
                allow_none=False,
            )
        )

        metric = str(
            self._single_value(
                working,
                "metric",
                allow_none=False,
            )
        )

        artifact_id = str(
            self._single_value(
                working,
                "artifact_id",
                allow_none=False,
            )
        )

        artifact_kind = str(
            self._single_value(
                working,
                "artifact_kind",
                allow_none=False,
            )
        )

        method_value = self._single_value(
            working,
            "method",
            allow_none=True,
        )

        method = None if method_value is None else str(method_value)

        transform = str(
            self._single_value(
                working,
                "transform",
                allow_none=False,
            )
        )

        transform_version = str(
            self._single_value(
                working,
                "transform_version",
                allow_none=False,
            )
        )

        raw_sha256 = self._artifact_provenance(
            artifact_id=artifact_id,
            source=source,
            dataset=dataset,
        )

        disk = self._disk_frame(working)

        logical_sha256 = self._logical_sha256(disk)

        identity = {
            "schema": SCHEMA_VERSION,
            "source": source,
            "dataset": dataset,
            "metric": metric,
            "artifact_id": artifact_id,
            "raw_sha256": raw_sha256,
            "artifact_kind": artifact_kind,
            "method": method,
            "transform": transform,
            "transform_version": transform_version,
            "requested_start": start.isoformat(),
            "requested_end": end.isoformat(),
            "logical_sha256": logical_sha256,
        }

        store_id = hashlib.sha256(
            json.dumps(
                identity,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        existing = self._record(store_id)

        if existing is not None:
            self._verify_record(existing)
            return existing

        observed_start = working["timestamp"].min()

        observed_end = working["timestamp"].max()

        relative = self._relative_path(
            source=source,
            dataset=dataset,
            metric=metric,
            year=int(observed_start.year),
            store_id=store_id,
        )

        target = self.root / relative

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = target.with_name("." + target.name + "." + uuid4().hex + ".tmp")

        replaced = False

        try:
            self._write_parquet(
                disk,
                temporary,
            )

            self._validate_parquet(
                temporary,
                expected_rows=len(disk),
                expected_logical_sha256=(logical_sha256),
            )

            parquet_sha256 = self._file_sha256(temporary)

            os.replace(
                temporary,
                target,
            )

            replaced = True

            created_at = datetime.now(UTC)

            self.con.execute("BEGIN")

            try:
                self.con.execute(
                    """
                    INSERT INTO scientific_files (
                        store_id,
                        source,
                        dataset,
                        metric,
                        artifact_id,
                        raw_sha256,
                        artifact_kind,
                        method,
                        transform,
                        transform_version,
                        requested_start,
                        requested_end,
                        observed_start,
                        observed_end,
                        row_count,
                        logical_sha256,
                        parquet_sha256,
                        path,
                        created_at
                    )
                    VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?
                    )
                    ON CONFLICT DO NOTHING
                    """,
                    [
                        store_id,
                        source,
                        dataset,
                        metric,
                        artifact_id,
                        raw_sha256,
                        artifact_kind,
                        method,
                        transform,
                        transform_version,
                        start.to_pydatetime(),
                        end.to_pydatetime(),
                        observed_start.to_pydatetime(),
                        observed_end.to_pydatetime(),
                        len(disk),
                        logical_sha256,
                        parquet_sha256,
                        str(relative),
                        created_at,
                    ],
                )

                self.con.execute("COMMIT")

            except Exception:
                self.con.execute("ROLLBACK")
                raise

        except Exception:
            if temporary.exists():
                temporary.unlink()

            if replaced:
                record = self._record(store_id)

                if record is None and target.exists():
                    target.unlink()

            raise

        result = self._record(store_id)

        if result is None:
            raise RuntimeError("Scientific file metadata was not registered.")

        self._verify_record(result)

        return result

    def read_store(
        self,
        store_id: str,
    ) -> pd.DataFrame:
        record = self._record(store_id)

        if record is None:
            raise KeyError(f"Unknown scientific store_id: {store_id}")

        self._verify_record(record)

        disk = self._read_parquet_disk(record.path)

        return self._memory_frame(disk)

    def query(
        self,
        *,
        start: Any,
        end: Any,
        metric: str | None = None,
        source: str | None = None,
        dataset: str | None = None,
    ) -> pd.DataFrame:
        start_ts = self._utc_timestamp(
            start,
            name="start",
        )
        end_ts = self._utc_timestamp(
            end,
            name="end",
        )

        if start_ts >= end_ts:
            raise ValueError("start must be before end.")

        query = """
            SELECT store_id
            FROM scientific_files
            WHERE requested_end > ?
              AND requested_start < ?
        """

        values: list[Any] = [
            start_ts.to_pydatetime(),
            end_ts.to_pydatetime(),
        ]

        if metric is not None:
            query += " AND metric = ?"
            values.append(metric)

        if source is not None:
            query += " AND source = ?"
            values.append(source)

        if dataset is not None:
            query += " AND dataset = ?"
            values.append(dataset)

        query += """
            ORDER BY
                metric,
                source,
                dataset,
                requested_start,
                store_id
        """

        store_ids = [
            row[0]
            for row in self.con.execute(
                query,
                values,
            ).fetchall()
        ]

        if not store_ids:
            return pd.DataFrame(columns=CANONICAL_COLUMNS)

        frames = [self.read_store(store_id) for store_id in store_ids]

        result = pd.concat(
            frames,
            ignore_index=True,
        )

        result = result[
            (result["timestamp"] >= start_ts) & (result["timestamp"] < end_ts)
        ].copy()

        return result.sort_values(
            [
                "metric",
                "timestamp",
                "source",
                "dataset",
                "artifact_id",
            ],
            kind="stable",
        ).reset_index(drop=True)

    def record_coverage(
        self,
        *,
        metric: str,
        source: str,
        dataset: str,
        artifact_id: str,
        transform: str,
        transform_version: str,
        requested_start: Any,
        requested_end: Any,
        row_count: int,
        store_id: str | None,
    ) -> str:
        start = self._utc_timestamp(
            requested_start,
            name="requested_start",
        )
        end = self._utc_timestamp(
            requested_end,
            name="requested_end",
        )

        if start >= end:
            raise ValueError("requested_start must be before requested_end.")

        if row_count < 0:
            raise ValueError("row_count must be >= 0.")

        if row_count == 0 and store_id is not None:
            raise ValueError(
                "Zero-row scientific coverage must not reference a store_id."
            )

        if row_count > 0 and store_id is None:
            raise ValueError("Non-empty scientific coverage must reference a store_id.")

        raw_sha256 = self._artifact_provenance(
            artifact_id=artifact_id,
            source=source,
            dataset=dataset,
        )

        if store_id is not None:
            record = self._record(store_id)

            if record is None:
                raise ValueError("Scientific coverage references an unknown store_id.")

            if (
                record.metric != metric
                or record.source != source
                or record.dataset != dataset
                or record.artifact_id != artifact_id
            ):
                raise ValueError(
                    "Scientific coverage does not match the referenced scientific file."
                )

            if record.row_count != row_count:
                raise ValueError(
                    "Scientific coverage row_count does not match the scientific file."
                )

            record_start = self._utc_timestamp(
                record.requested_start,
                name="record.requested_start",
            )
            record_end = self._utc_timestamp(
                record.requested_end,
                name="record.requested_end",
            )

            if record_start != start or record_end != end:
                raise ValueError(
                    "Scientific coverage interval does not match the scientific file."
                )

        identity = {
            "schema": COVERAGE_SCHEMA_VERSION,
            "source": source,
            "dataset": dataset,
            "metric": metric,
            "artifact_id": artifact_id,
            "raw_sha256": raw_sha256,
            "transform": transform,
            "transform_version": transform_version,
            "requested_start": start.isoformat(),
            "requested_end": end.isoformat(),
            "row_count": row_count,
            "store_id": store_id,
        }

        coverage_id = hashlib.sha256(
            json.dumps(
                identity,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        self.con.execute(
            """
            INSERT INTO scientific_coverage (
                coverage_id,
                source,
                dataset,
                metric,
                artifact_id,
                raw_sha256,
                transform,
                transform_version,
                requested_start,
                requested_end,
                row_count,
                store_id,
                created_at
            )
            VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?
            )
            ON CONFLICT DO NOTHING
            """,
            [
                coverage_id,
                source,
                dataset,
                metric,
                artifact_id,
                raw_sha256,
                transform,
                transform_version,
                start.to_pydatetime(),
                end.to_pydatetime(),
                row_count,
                store_id,
                datetime.now(UTC),
            ],
        )

        return coverage_id

    def query_coverage(
        self,
        *,
        metric: str,
        source: str,
        dataset: str,
        transform: str,
        transform_version: str,
        start: Any,
        end: Any,
    ) -> pd.DataFrame:
        start_ts = self._utc_timestamp(
            start,
            name="start",
        )
        end_ts = self._utc_timestamp(
            end,
            name="end",
        )

        if start_ts >= end_ts:
            raise ValueError("start must be before end.")

        rows = self.con.execute(
            """
            SELECT DISTINCT store_id
            FROM scientific_coverage
            WHERE metric = ?
              AND source = ?
              AND dataset = ?
              AND transform = ?
              AND transform_version = ?
              AND store_id IS NOT NULL
              AND requested_end > ?
              AND requested_start < ?
            ORDER BY store_id
            """,
            [
                metric,
                source,
                dataset,
                transform,
                transform_version,
                start_ts.to_pydatetime(),
                end_ts.to_pydatetime(),
            ],
        ).fetchall()

        store_ids = [row[0] for row in rows]

        if not store_ids:
            return pd.DataFrame(columns=CANONICAL_COLUMNS)

        frames = [self.read_store(store_id) for store_id in store_ids]

        result = pd.concat(
            frames,
            ignore_index=True,
        )

        result = result[
            (result["timestamp"] >= start_ts)
            & (result["timestamp"] < end_ts)
            & (result["metric"] == metric)
            & (result["source"] == source)
            & (result["dataset"] == dataset)
        ].copy()

        return result.sort_values(
            [
                "metric",
                "timestamp",
                "source",
                "dataset",
                "artifact_id",
            ],
            kind="stable",
        ).reset_index(drop=True)

    def missing_ranges(
        self,
        *,
        metric: str,
        source: str,
        dataset: str,
        transform: str,
        transform_version: str,
        start: Any,
        end: Any,
    ) -> list[
        tuple[
            pd.Timestamp,
            pd.Timestamp,
        ]
    ]:
        start_ts = self._utc_timestamp(
            start,
            name="start",
        )
        end_ts = self._utc_timestamp(
            end,
            name="end",
        )

        if start_ts >= end_ts:
            raise ValueError("start must be before end.")

        rows = self.con.execute(
            """
            SELECT
                requested_start,
                requested_end
            FROM scientific_coverage
            WHERE metric = ?
              AND source = ?
              AND dataset = ?
              AND transform = ?
              AND transform_version = ?
              AND requested_end > ?
              AND requested_start < ?
            ORDER BY
                requested_start,
                requested_end
            """,
            [
                metric,
                source,
                dataset,
                transform,
                transform_version,
                start_ts.to_pydatetime(),
                end_ts.to_pydatetime(),
            ],
        ).fetchall()

        cursor = start_ts
        missing = []

        for covered_start, covered_end in rows:
            covered_start = self._utc_timestamp(
                covered_start,
                name="covered_start",
            )
            covered_end = self._utc_timestamp(
                covered_end,
                name="covered_end",
            )

            if covered_end <= cursor:
                continue

            if covered_start > cursor:
                missing.append(
                    (
                        cursor,
                        min(
                            covered_start,
                            end_ts,
                        ),
                    )
                )

            cursor = max(
                cursor,
                covered_end,
            )

            if cursor >= end_ts:
                break

        if cursor < end_ts:
            missing.append(
                (
                    cursor,
                    end_ts,
                )
            )

        return missing
