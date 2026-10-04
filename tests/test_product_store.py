import duckdb
import pandas as pd
import pytest

from orbitoby.warehouse.products import (
    ProductParent,
    ProductStore,
)


def connection():
    con = duckdb.connect(":memory:")

    con.execute("SET TimeZone = 'UTC'")

    con.execute(
        """
        CREATE TABLE artifacts (
            artifact_id VARCHAR PRIMARY KEY,
            source VARCHAR NOT NULL,
            dataset VARCHAR NOT NULL,
            norad_id INTEGER,
            requested_start DATE,
            requested_end DATE,
            retrieved_at TIMESTAMPTZ,
            sha256 VARCHAR NOT NULL,
            path VARCHAR
        )
        """
    )

    con.execute(
        """
        INSERT INTO artifacts (
            artifact_id,
            source,
            dataset,
            retrieved_at,
            sha256,
            path
        )
        VALUES (
            'raw-1',
            'gfz',
            'kp',
            TIMESTAMPTZ
                '2024-01-02 00:00:00+00',
            'sha-1',
            '/tmp/raw-1'
        )
        """
    )

    return con


def product_frame():
    return pd.DataFrame(
        [
            {
                "timestamp": pd.Timestamp("2024-01-01T00:00:00Z"),
                "value": 1.2e-12,
                "is_missing": False,
                "missing_reason": None,
                "interval_start": None,
                "interval_end": None,
                "context": {
                    "altitude_km": 400.0,
                },
            },
            {
                "timestamp": pd.Timestamp("2024-01-01T03:00:00Z"),
                "value": 1.4e-12,
                "is_missing": False,
                "missing_reason": None,
                "interval_start": None,
                "interval_end": None,
                "context": {
                    "altitude_km": 402.0,
                },
            },
        ]
    )


def write_model(
    store,
    *,
    model_version="2.0",
):
    return store.write(
        product_frame(),
        dataset="msis_density",
        metric=("thermosphere_neutral_mass_density"),
        unit="kg/m^3",
        artifact_kind="model_output",
        method="msis",
        model_name="MSIS",
        model_version=model_version,
        transform="msis_density",
        transform_version="1",
        requested_start="2024-01-01",
        requested_end="2024-01-02",
        parents=[
            ProductParent(
                parent_kind="raw_artifact",
                parent_id="raw-1",
                role="space_weather_input",
            )
        ],
        parameters={
            "altitude_reference": "geodetic",
        },
    )


def test_model_product_round_trip(
    tmp_path,
):
    con = connection()

    store = ProductStore(
        con,
        root=tmp_path,
    )

    saved = write_model(store)

    result = store.read_product(saved.product_id)

    assert len(result) == 2

    assert set(result["artifact_kind"]) == {"model_output"}

    assert set(result["model_name"]) == {"MSIS"}

    assert set(result["model_version"]) == {"2.0"}

    assert result.loc[
        0,
        "context",
    ] == {
        "altitude_km": 400.0,
    }


def test_model_output_requires_model_identity(
    tmp_path,
):
    store = ProductStore(
        connection(),
        root=tmp_path,
    )

    with pytest.raises(
        ValueError,
        match="model_name",
    ):
        store.write(
            product_frame(),
            dataset="density",
            metric="density",
            unit="kg/m^3",
            artifact_kind="model_output",
            method="model",
            transform="model",
            transform_version="1",
            model_version="1",
            requested_start="2024-01-01",
            requested_end="2024-01-02",
            parents=[
                ProductParent(
                    "raw_artifact",
                    "raw-1",
                )
            ],
        )


def test_orbitoby_derived_is_not_model(
    tmp_path,
):
    store = ProductStore(
        connection(),
        root=tmp_path,
    )

    with pytest.raises(
        ValueError,
        match="must not declare",
    ):
        store.write(
            product_frame(),
            dataset="derived_density",
            metric="density",
            unit="kg/m^3",
            artifact_kind=("orbitoby_derived"),
            method="derive",
            model_name="fake",
            model_version="1",
            transform="derive",
            transform_version="1",
            requested_start="2024-01-01",
            requested_end="2024-01-02",
            parents=[
                ProductParent(
                    "raw_artifact",
                    "raw-1",
                )
            ],
        )


def test_unknown_parent_rejected(
    tmp_path,
):
    store = ProductStore(
        connection(),
        root=tmp_path,
    )

    with pytest.raises(
        ValueError,
        match="unknown parent",
    ):
        store.write(
            product_frame(),
            dataset="derived",
            metric="x",
            unit="1",
            artifact_kind=("orbitoby_derived"),
            method="derive",
            transform="derive",
            transform_version="1",
            requested_start="2024-01-01",
            requested_end="2024-01-02",
            parents=[
                ProductParent(
                    "raw_artifact",
                    "missing",
                )
            ],
        )


def test_product_write_is_idempotent(
    tmp_path,
):
    store = ProductStore(
        connection(),
        root=tmp_path,
    )

    first = write_model(store)
    second = write_model(store)

    assert first.product_id == second.product_id

    count = store.con.execute(
        """
        SELECT COUNT(*)
        FROM derived_products
        """
    ).fetchone()[0]

    assert count == 1


def test_model_version_changes_identity(
    tmp_path,
):
    store = ProductStore(
        connection(),
        root=tmp_path,
    )

    first = write_model(
        store,
        model_version="2.0",
    )

    second = write_model(
        store,
        model_version="2.1",
    )

    assert first.product_id != second.product_id


def test_lineage_is_preserved(
    tmp_path,
):
    store = ProductStore(
        connection(),
        root=tmp_path,
    )

    saved = write_model(store)

    parents = store.lineage(saved.product_id)

    assert parents == (
        ProductParent(
            parent_kind="raw_artifact",
            parent_id="raw-1",
            role="space_weather_input",
        ),
    )


def test_corruption_detected(
    tmp_path,
):
    store = ProductStore(
        connection(),
        root=tmp_path,
    )

    saved = write_model(store)

    with saved.path.open("ab") as handle:
        handle.write(b"corruption")

    with pytest.raises(
        RuntimeError,
        match="checksum",
    ):
        store.read_product(saved.product_id)


def test_missing_semantics_are_explicit(
    tmp_path,
):
    store = ProductStore(
        connection(),
        root=tmp_path,
    )

    data = product_frame()

    data.loc[
        0,
        "value",
    ] = None

    data.loc[
        0,
        "is_missing",
    ] = False

    with pytest.raises(
        ValueError,
        match="is_missing",
    ):
        store.write(
            data,
            dataset="derived",
            metric="x",
            unit="1",
            artifact_kind=("orbitoby_derived"),
            method="derive",
            transform="derive",
            transform_version="1",
            requested_start="2024-01-01",
            requested_end="2024-01-02",
            parents=[
                ProductParent(
                    "raw_artifact",
                    "raw-1",
                )
            ],
        )


def test_db_registration_failure_removes_replaced_product(
    tmp_path,
):
    con = connection()

    store = ProductStore(
        con,
        root=tmp_path,
    )

    class FailingConnection:
        def __init__(
            self,
            wrapped,
        ):
            self.wrapped = wrapped

        def execute(
            self,
            sql,
            parameters=None,
        ):
            if "INSERT INTO derived_products" in str(sql):
                raise RuntimeError("simulated DB registration failure")

            if parameters is None:
                return self.wrapped.execute(sql)

            return self.wrapped.execute(
                sql,
                parameters,
            )

        def executemany(
            self,
            sql,
            parameters,
        ):
            return self.wrapped.executemany(
                sql,
                parameters,
            )

    store.con = FailingConnection(con)

    with pytest.raises(
        RuntimeError,
        match="simulated DB registration failure",
    ):
        write_model(store)

    product_count = con.execute(
        """
        SELECT COUNT(*)
        FROM derived_products
        """
    ).fetchone()[0]

    lineage_count = con.execute(
        """
        SELECT COUNT(*)
        FROM product_lineage
        """
    ).fetchone()[0]

    assert product_count == 0
    assert lineage_count == 0

    assert list(tmp_path.rglob("*.parquet")) == []

    assert list(tmp_path.rglob("*.tmp")) == []
