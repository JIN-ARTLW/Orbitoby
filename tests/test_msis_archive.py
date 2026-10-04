from __future__ import annotations

import json
from datetime import UTC, datetime

import duckdb
import pandas as pd
import pytest

from orbitoby import service
from orbitoby.models.msis import (
    MSISRun,
)
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

    for artifact_id, dataset in (
        ("f107-raw", "f107"),
        ("ap-raw", "ap"),
    ):
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
                ?,
                'test',
                ?,
                ?,
                ?,
                ?
            )
            """,
            [
                artifact_id,
                dataset,
                datetime.now(UTC),
                f"sha-{artifact_id}",
                f"/tmp/{artifact_id}",
            ],
        )

    return con


def inputs():
    return pd.DataFrame(
        {
            "timestamp": [
                "2024-05-10T00:00:00Z",
                "2024-05-10T03:00:00Z",
            ],
        }
    )


def fake_run():
    return MSISRun(
        data=pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    [
                        "2024-05-10T00:00:00Z",
                        "2024-05-10T03:00:00Z",
                    ],
                    utc=True,
                ),
                "value": pd.Series(
                    [
                        1.2e-12,
                        1.4e-12,
                    ],
                    dtype="Float64",
                ),
                "is_missing": [
                    False,
                    False,
                ],
                "missing_reason": [
                    None,
                    None,
                ],
                "interval_start": [
                    pd.NaT,
                    pd.NaT,
                ],
                "interval_end": [
                    pd.NaT,
                    pd.NaT,
                ],
                "context": [
                    {
                        "altitude_km": 400.0,
                    },
                    {
                        "altitude_km": 401.0,
                    },
                ],
            }
        ),
        model_name="NRLMSIS",
        model_version="2.1",
        backend="pymsis",
        backend_version="0.13.0",
        geomagnetic_activity=-1,
        interpolate_indices=False,
    )


def parents():
    return [
        ProductParent(
            parent_kind="raw_artifact",
            parent_id="f107-raw",
            role=("f107_previous_day_input"),
        ),
        ProductParent(
            parent_kind="raw_artifact",
            parent_id="f107-raw",
            role=("f107a_81day_input"),
        ),
        ProductParent(
            parent_kind="raw_artifact",
            parent_id="ap-raw",
            role="ap_input",
        ),
    ]


def archive(tmp_path):
    result = service.Archive.__new__(service.Archive)

    result.con = connection()

    result.product_store = ProductStore(
        result.con,
        root=tmp_path,
    )

    return result


def test_archive_msis_persists_model_output(
    tmp_path,
    monkeypatch,
):
    instance = archive(tmp_path)

    monkeypatch.setattr(
        service,
        "calculate_msis_density",
        lambda inputs, *, geomagnetic_activity: fake_run(),
    )

    result = instance.msis_density(
        inputs(),
        parents=parents(),
    )

    assert len(result) == 2

    assert set(result["artifact_kind"]) == {"model_output"}

    assert set(result["model_name"]) == {"NRLMSIS"}

    assert set(result["model_version"]) == {"2.1"}


def test_archive_msis_preserves_lineage(
    tmp_path,
    monkeypatch,
):
    instance = archive(tmp_path)

    monkeypatch.setattr(
        service,
        "calculate_msis_density",
        lambda inputs, *, geomagnetic_activity: fake_run(),
    )

    result = instance.msis_density(
        inputs(),
        parents=parents(),
    )

    product_id = result.loc[
        0,
        "product_id",
    ]

    lineage = instance.product_store.lineage(product_id)

    assert {parent.role for parent in lineage} == {
        "f107_previous_day_input",
        "f107a_81day_input",
        "ap_input",
    }


def test_archive_msis_requires_driver_lineage(
    tmp_path,
):
    instance = archive(tmp_path)

    with pytest.raises(
        ValueError,
        match="ap_input",
    ):
        instance.msis_density(
            inputs(),
            parents=[
                ProductParent(
                    parent_kind=("raw_artifact"),
                    parent_id="f107-raw",
                    role=("f107_previous_day_input"),
                ),
                ProductParent(
                    parent_kind=("raw_artifact"),
                    parent_id="f107-raw",
                    role=("f107a_81day_input"),
                ),
            ],
        )


def test_archive_msis_records_backend_policy(
    tmp_path,
    monkeypatch,
):
    instance = archive(tmp_path)

    monkeypatch.setattr(
        service,
        "calculate_msis_density",
        lambda inputs, *, geomagnetic_activity: fake_run(),
    )

    result = instance.msis_density(
        inputs(),
        parents=parents(),
    )

    product_id = result.loc[
        0,
        "product_id",
    ]

    row = instance.con.execute(
        """
        SELECT parameters_json
        FROM derived_products
        WHERE product_id = ?
        """,
        [product_id],
    ).fetchone()

    parameters = json.loads(row[0])

    assert parameters["backend"] == "pymsis"

    assert parameters["backend_version"] == "0.13.0"

    assert parameters["forcing_policy"] == "explicit_only"

    assert parameters["interpolate_indices"] is False


def test_product_parent_is_public_api():
    from orbitoby import (
        ProductParent as PublicParent,
    )

    assert PublicParent is ProductParent
