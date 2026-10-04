from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import duckdb
import pandas as pd

from orbitoby.config import WAREHOUSE_DIR
from orbitoby.warehouse.scientific import ScientificStore

PRODUCT_SCHEMA_VERSION = "derived-product-v1"

ALLOWED_ARTIFACT_KINDS = {
    "orbitoby_derived",
    "model_output",
}

ALLOWED_PARENT_KINDS = {
    "raw_artifact",
    "scientific_file",
    "derived_product",
}


SCHEMA = """
CREATE TABLE IF NOT EXISTS derived_products (
    product_id VARCHAR PRIMARY KEY,

    source VARCHAR NOT NULL,
    dataset VARCHAR NOT NULL,
    metric VARCHAR NOT NULL,
    unit VARCHAR NOT NULL,

    artifact_kind VARCHAR NOT NULL,
    method VARCHAR NOT NULL,

    model_name VARCHAR,
    model_version VARCHAR,

    transform VARCHAR NOT NULL,
    transform_version VARCHAR NOT NULL,

    requested_start TIMESTAMPTZ NOT NULL,
    requested_end TIMESTAMPTZ NOT NULL,

    observed_start TIMESTAMPTZ NOT NULL,
    observed_end TIMESTAMPTZ NOT NULL,

    row_count BIGINT NOT NULL,

    parameters_json VARCHAR NOT NULL,

    logical_sha256 VARCHAR NOT NULL,
    parquet_sha256 VARCHAR NOT NULL,

    path VARCHAR NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS derived_product_lookup
ON derived_products (
    metric,
    dataset,
    artifact_kind,
    requested_start,
    requested_end
);

CREATE TABLE IF NOT EXISTS product_lineage (
    product_id VARCHAR NOT NULL,

    parent_kind VARCHAR NOT NULL,
    parent_id VARCHAR NOT NULL,
    role VARCHAR NOT NULL,

    PRIMARY KEY (
        product_id,
        parent_kind,
        parent_id,
        role
    )
);

CREATE INDEX IF NOT EXISTS product_lineage_parent
ON product_lineage (
    parent_kind,
    parent_id
);
"""


INPUT_COLUMNS = (
    "timestamp",
    "value",
    "is_missing",
    "missing_reason",
    "interval_start",
    "interval_end",
    "context",
)


DISK_COLUMNS = (
    "timestamp",
    "metric",
    "value",
    "unit",
    "is_missing",
    "missing_reason",
    "source",
    "dataset",
    "artifact_kind",
    "method",
    "model_name",
    "model_version",
    "interval_start",
    "interval_end",
    "transform",
    "transform_version",
    "context_json",
)


RESULT_COLUMNS = (
    "timestamp",
    "metric",
    "value",
    "unit",
    "is_missing",
    "missing_reason",
    "source",
    "dataset",
    "artifact_kind",
    "method",
    "model_name",
    "model_version",
    "interval_start",
    "interval_end",
    "product_id",
    "transform",
    "transform_version",
    "context",
)


@dataclass(frozen=True, slots=True)
class ProductParent:
    parent_kind: str
    parent_id: str
    role: str = "input"


@dataclass(frozen=True, slots=True)
class ProductRecord:
    product_id: str

    source: str
    dataset: str
    metric: str
    unit: str

    artifact_kind: str
    method: str

    model_name: str | None
    model_version: str | None

    transform: str
    transform_version: str

    requested_start: datetime
    requested_end: datetime

    observed_start: datetime
    observed_end: datetime

    row_count: int

    parameters_json: str

    logical_sha256: str
    parquet_sha256: str

    path: Path
    created_at: datetime


class ProductStore:
    """Storage for Orbitoby-derived and physical-model products."""

    def __init__(
        self,
        con: duckdb.DuckDBPyConnection,
        *,
        root: str | Path | None = None,
    ) -> None:
        self.con = con

        self.con.execute("SET TimeZone = 'UTC'")

        self.root = (
            Path(root if root is not None else WAREHOUSE_DIR / "products")
            .expanduser()
            .resolve()
        )

        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.con.execute(SCHEMA)

    @staticmethod
    def _partition_component(
        value: str,
    ) -> str:
        return quote(
            value,
            safe="-_.",
        )

    @staticmethod
    def _required_columns(
        frame: pd.DataFrame,
    ) -> None:
        missing = set(INPUT_COLUMNS) - set(frame.columns)

        if missing:
            raise ValueError(
                "Derived product frame is "
                "missing columns: " + ", ".join(sorted(missing))
            )

    @staticmethod
    def _validate_metadata(
        *,
        artifact_kind: str,
        method: str,
        model_name: str | None,
        model_version: str | None,
    ) -> None:
        if artifact_kind not in (ALLOWED_ARTIFACT_KINDS):
            raise ValueError(
                "artifact_kind must be 'orbitoby_derived' or 'model_output'."
            )

        if not method:
            raise ValueError("method must not be empty.")

        if artifact_kind == "model_output":
            if not model_name:
                raise ValueError("model_output requires model_name.")

            if not model_version:
                raise ValueError("model_output requires model_version.")

        if artifact_kind == "orbitoby_derived" and (
            model_name is not None or model_version is not None
        ):
            raise ValueError(
                "orbitoby_derived must not declare model_name or model_version."
            )

    def _validate_parent(
        self,
        parent: ProductParent,
    ) -> None:
        if parent.parent_kind not in ALLOWED_PARENT_KINDS:
            raise ValueError(f"Unsupported parent_kind: {parent.parent_kind!r}")

        if not parent.parent_id:
            raise ValueError("parent_id must not be empty.")

        if not parent.role:
            raise ValueError("parent role must not be empty.")

        if parent.parent_kind == "raw_artifact":
            query = """
                SELECT 1
                FROM artifacts
                WHERE artifact_id = ?
            """

        elif parent.parent_kind == "scientific_file":
            query = """
                SELECT 1
                FROM scientific_files
                WHERE store_id = ?
            """

        else:
            query = """
                SELECT 1
                FROM derived_products
                WHERE product_id = ?
            """

        exists = self.con.execute(
            query,
            [parent.parent_id],
        ).fetchone()

        if exists is None:
            raise ValueError(
                "Derived product references "
                "an unknown parent: "
                f"{parent.parent_kind}/"
                f"{parent.parent_id}"
            )

    @classmethod
    def _prepare_frame(
        cls,
        frame: pd.DataFrame,
        *,
        metric: str,
        unit: str,
        dataset: str,
        artifact_kind: str,
        method: str,
        model_name: str | None,
        model_version: str | None,
        transform: str,
        transform_version: str,
    ) -> pd.DataFrame:
        cls._required_columns(frame)

        result = frame.loc[
            :,
            list(INPUT_COLUMNS),
        ].copy()

        result["timestamp"] = pd.to_datetime(
            result["timestamp"],
            utc=True,
            errors="raise",
        )

        for column in (
            "interval_start",
            "interval_end",
        ):
            result[column] = pd.to_datetime(
                result[column],
                utc=True,
                errors="coerce",
            )

        mismatched_interval = (
            result["interval_start"].isna() != result["interval_end"].isna()
        )

        if mismatched_interval.any():
            raise ValueError(
                "interval_start and interval_end must both be null or both be set."
            )

        valid_intervals = result["interval_start"].notna()

        if (
            result.loc[
                valid_intervals,
                "interval_start",
            ]
            >= result.loc[
                valid_intervals,
                "interval_end",
            ]
        ).any():
            raise ValueError("interval_start must be before interval_end.")

        result["value"] = pd.to_numeric(
            result["value"],
            errors="raise",
        ).astype("Float64")

        result["is_missing"] = result["is_missing"].astype("boolean")

        if result["is_missing"].isna().any():
            raise ValueError("is_missing must not contain null.")

        actual_missing = result["value"].isna()

        declared_missing = result["is_missing"].astype(bool)

        if not actual_missing.equals(declared_missing):
            raise ValueError("value nullability and is_missing disagree.")

        result["missing_reason"] = ScientificStore._nullable_string(
            result["missing_reason"]
        )

        result["context_json"] = result["context"].map(ScientificStore._json_dumps)

        result = result.drop(columns=["context"])

        result["metric"] = metric
        result["unit"] = unit
        result["source"] = "orbitoby"
        result["dataset"] = dataset
        result["artifact_kind"] = artifact_kind
        result["method"] = method

        result["model_name"] = pd.NA if model_name is None else model_name

        result["model_version"] = pd.NA if model_version is None else model_version

        result["transform"] = transform
        result["transform_version"] = transform_version

        for column in (
            "metric",
            "unit",
            "source",
            "dataset",
            "artifact_kind",
            "method",
            "model_name",
            "model_version",
            "transform",
            "transform_version",
        ):
            result[column] = ScientificStore._nullable_string(result[column])

        return result.loc[
            :,
            list(DISK_COLUMNS),
        ]

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

        try:
            con.execute("SET TimeZone = 'UTC'")

            con.register(
                "_orbitoby_product",
                frame,
            )

            target = self._sql_path(path)

            con.execute(
                f"""
                COPY _orbitoby_product
                TO '{target}'
                (
                    FORMAT PARQUET,
                    COMPRESSION ZSTD
                )
                """
            )

        finally:
            con.close()

    def _read_parquet(
        self,
        path: Path,
    ) -> pd.DataFrame:
        con = duckdb.connect()

        try:
            con.execute("SET TimeZone = 'UTC'")

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
        row_count: int,
        logical_sha256: str,
    ) -> None:
        frame = self._read_parquet(path)

        if tuple(frame.columns) != DISK_COLUMNS:
            raise RuntimeError("Derived Parquet schema mismatch.")

        if len(frame) != row_count:
            raise RuntimeError("Derived Parquet row-count mismatch.")

        actual = ScientificStore._logical_sha256(frame)

        if actual != logical_sha256:
            raise RuntimeError("Derived Parquet read-back validation failed.")

    def _record(
        self,
        product_id: str,
    ) -> ProductRecord | None:
        row = self.con.execute(
            """
            SELECT
                product_id,
                source,
                dataset,
                metric,
                unit,
                artifact_kind,
                method,
                model_name,
                model_version,
                transform,
                transform_version,
                requested_start,
                requested_end,
                observed_start,
                observed_end,
                row_count,
                parameters_json,
                logical_sha256,
                parquet_sha256,
                path,
                created_at
            FROM derived_products
            WHERE product_id = ?
            """,
            [product_id],
        ).fetchone()

        if row is None:
            return None

        return ProductRecord(
            product_id=row[0],
            source=row[1],
            dataset=row[2],
            metric=row[3],
            unit=row[4],
            artifact_kind=row[5],
            method=row[6],
            model_name=row[7],
            model_version=row[8],
            transform=row[9],
            transform_version=row[10],
            requested_start=row[11],
            requested_end=row[12],
            observed_start=row[13],
            observed_end=row[14],
            row_count=row[15],
            parameters_json=row[16],
            logical_sha256=row[17],
            parquet_sha256=row[18],
            path=self.root / row[19],
            created_at=row[20],
        )

    def _verify_record(
        self,
        record: ProductRecord,
    ) -> None:
        path = record.path.resolve()

        if not path.is_relative_to(self.root):
            raise RuntimeError("Derived product path escapes storage root.")

        if not path.is_file():
            raise RuntimeError("Derived product Parquet is missing.")

        sha256 = ScientificStore._file_sha256(path)

        if sha256 != record.parquet_sha256:
            raise RuntimeError("Derived product checksum mismatch.")

        self._validate_parquet(
            path,
            row_count=record.row_count,
            logical_sha256=(record.logical_sha256),
        )

    def write(
        self,
        frame: pd.DataFrame,
        *,
        dataset: str,
        metric: str,
        unit: str,
        artifact_kind: str,
        method: str,
        transform: str,
        transform_version: str,
        requested_start: Any,
        requested_end: Any,
        parents: Iterable[ProductParent],
        parameters: dict[str, Any] | None = None,
        model_name: str | None = None,
        model_version: str | None = None,
    ) -> ProductRecord:
        if not isinstance(
            frame,
            pd.DataFrame,
        ):
            raise TypeError("frame must be a pandas DataFrame.")

        if frame.empty:
            raise ValueError("Cannot persist an empty derived product.")

        self._validate_metadata(
            artifact_kind=artifact_kind,
            method=method,
            model_name=model_name,
            model_version=model_version,
        )

        start = ScientificStore._utc_timestamp(
            requested_start,
            name="requested_start",
        )

        end = ScientificStore._utc_timestamp(
            requested_end,
            name="requested_end",
        )

        if start >= end:
            raise ValueError("requested_start must be before requested_end.")

        parents = tuple(parents)

        if not parents:
            raise ValueError("Derived products require at least one provenance parent.")

        for parent in parents:
            self._validate_parent(parent)

        disk = self._prepare_frame(
            frame,
            metric=metric,
            unit=unit,
            dataset=dataset,
            artifact_kind=artifact_kind,
            method=method,
            model_name=model_name,
            model_version=model_version,
            transform=transform,
            transform_version=(transform_version),
        )

        outside = (disk["timestamp"] < start) | (disk["timestamp"] >= end)

        if outside.any():
            raise ValueError(
                "Derived frame contains rows outside requested [start, end)."
            )

        logical_sha256 = ScientificStore._logical_sha256(disk)

        parameters_json = ScientificStore._json_dumps(parameters or {})

        lineage = sorted(
            (
                parent.parent_kind,
                parent.parent_id,
                parent.role,
            )
            for parent in parents
        )

        identity = {
            "schema": PRODUCT_SCHEMA_VERSION,
            "source": "orbitoby",
            "dataset": dataset,
            "metric": metric,
            "unit": unit,
            "artifact_kind": (artifact_kind),
            "method": method,
            "model_name": model_name,
            "model_version": (model_version),
            "transform": transform,
            "transform_version": (transform_version),
            "requested_start": (start.isoformat()),
            "requested_end": (end.isoformat()),
            "parameters_json": (parameters_json),
            "lineage": lineage,
            "logical_sha256": (logical_sha256),
        }

        product_id = hashlib.sha256(
            json.dumps(
                identity,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        existing = self._record(product_id)

        if existing is not None:
            self._verify_record(existing)
            return existing

        observed_start = disk["timestamp"].min()

        observed_end = disk["timestamp"].max()

        relative = (
            Path("source=orbitoby")
            / ("dataset=" + self._partition_component(dataset))
            / ("metric=" + self._partition_component(metric))
            / (f"year={observed_start.year:04d}")
            / f"{product_id}.parquet"
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
                row_count=len(disk),
                logical_sha256=(logical_sha256),
            )

            parquet_sha256 = ScientificStore._file_sha256(temporary)

            os.replace(
                temporary,
                target,
            )

            replaced = True

            self.con.execute("BEGIN")

            try:
                self.con.execute(
                    """
                    INSERT INTO derived_products (
                        product_id,
                        source,
                        dataset,
                        metric,
                        unit,
                        artifact_kind,
                        method,
                        model_name,
                        model_version,
                        transform,
                        transform_version,
                        requested_start,
                        requested_end,
                        observed_start,
                        observed_end,
                        row_count,
                        parameters_json,
                        logical_sha256,
                        parquet_sha256,
                        path,
                        created_at
                    )
                    VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?
                    )
                    """,
                    [
                        product_id,
                        "orbitoby",
                        dataset,
                        metric,
                        unit,
                        artifact_kind,
                        method,
                        model_name,
                        model_version,
                        transform,
                        transform_version,
                        start.to_pydatetime(),
                        end.to_pydatetime(),
                        observed_start.to_pydatetime(),
                        observed_end.to_pydatetime(),
                        len(disk),
                        parameters_json,
                        logical_sha256,
                        parquet_sha256,
                        str(relative),
                        datetime.now(UTC),
                    ],
                )

                self.con.executemany(
                    """
                    INSERT INTO product_lineage (
                        product_id,
                        parent_kind,
                        parent_id,
                        role
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    [
                        (
                            product_id,
                            parent.parent_kind,
                            parent.parent_id,
                            parent.role,
                        )
                        for parent in parents
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
                record = self._record(product_id)

                if record is None and target.exists():
                    target.unlink()

            raise

        result = self._record(product_id)

        if result is None:
            raise RuntimeError("Derived product metadata was not registered.")

        self._verify_record(result)

        return result

    def read_product(
        self,
        product_id: str,
    ) -> pd.DataFrame:
        record = self._record(product_id)

        if record is None:
            raise KeyError(f"Unknown product_id: {product_id}")

        self._verify_record(record)

        frame = self._read_parquet(record.path)

        frame["context"] = frame["context_json"].map(ScientificStore._json_loads)

        frame = frame.drop(columns=["context_json"])

        frame["product_id"] = product_id

        for column in (
            "timestamp",
            "interval_start",
            "interval_end",
        ):
            frame[column] = pd.to_datetime(
                frame[column],
                utc=True,
            )

        return frame.loc[
            :,
            list(RESULT_COLUMNS),
        ]

    def lineage(
        self,
        product_id: str,
    ) -> tuple[
        ProductParent,
        ...,
    ]:
        if self._record(product_id) is None:
            raise KeyError(f"Unknown product_id: {product_id}")

        rows = self.con.execute(
            """
            SELECT
                parent_kind,
                parent_id,
                role
            FROM product_lineage
            WHERE product_id = ?
            ORDER BY
                role,
                parent_kind,
                parent_id
            """,
            [product_id],
        ).fetchall()

        return tuple(
            ProductParent(
                parent_kind=row[0],
                parent_id=row[1],
                role=row[2],
            )
            for row in rows
        )
