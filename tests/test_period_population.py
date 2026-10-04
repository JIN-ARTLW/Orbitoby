from datetime import UTC, datetime

import duckdb
import pytest

from orbitoby.catalogue import CatalogueAPI
from orbitoby.service import Archive
from orbitoby.sources.celestrak import (
    CelesTrakSource,
)
from orbitoby.warehouse.identity import SCHEMA


class LocalCatalogue(CatalogueAPI):
    def __init__(self):
        self.con = duckdb.connect(":memory:")
        self.con.execute(SCHEMA)


def insert_satcat(
    catalogue,
    *,
    object_id,
    norad_id,
    name,
    object_type,
    launch_date,
    decay_date=None,
    record_id=None,
):
    record_id = record_id or f"record-{norad_id}"

    catalogue.con.execute(
        """
        INSERT INTO objects(
            object_id,
            norad_id,
            cospar_id,
            name
        )
        VALUES (?, ?, NULL, ?)
        """,
        [
            object_id,
            norad_id,
            name,
        ],
    )

    data = {
        "OBJECT_NAME": name,
        "NORAD_CAT_ID": str(norad_id),
        "OBJECT_TYPE": object_type,
        "LAUNCH_DATE": launch_date,
        "DECAY_DATE": decay_date,
    }

    import json

    catalogue.con.execute(
        """
        INSERT INTO source_records(
            record_id,
            artifact_id,
            row_index,
            source,
            dataset,
            object_id,
            retrieved_at,
            data,
            identity_status,
            identity_detail
        )
        VALUES (
            ?,
            'artifact',
            ?,
            'celestrak',
            'satcat',
            ?,
            ?,
            ?,
            'linked',
            NULL
        )
        """,
        [
            record_id,
            norad_id,
            object_id,
            datetime(
                2026,
                1,
                1,
                tzinfo=UTC,
            ),
            json.dumps(data),
        ],
    )


def test_celestrak_bulk_satcat_normalization():
    payload = (
        b"OBJECT_NAME,OBJECT_ID,NORAD_CAT_ID,"
        b"OBJECT_TYPE,LAUNCH_DATE,DECAY_DATE\n"
        b"TESTSAT,2020-001A,12345,PAY,"
        b"2020-01-01,\n"
    )

    source = CelesTrakSource()

    rows = source.normalize(
        "satcat",
        payload,
        all=True,
    )

    assert len(rows) == 1
    assert rows[0]["OBJECT_NAME"] == "TESTSAT"
    assert rows[0]["OBJECT_TYPE"] == "PAY"
    assert rows[0]["LAUNCH_DATE"] == "2020-01-01"


def test_period_objects_overlap_and_throughout():
    catalogue = LocalCatalogue()

    insert_satcat(
        catalogue,
        object_id="a",
        norad_id=10001,
        name="A",
        object_type="PAY",
        launch_date="2020-01-01",
    )

    insert_satcat(
        catalogue,
        object_id="b",
        norad_id=10002,
        name="B",
        object_type="PAY",
        launch_date="2021-06-01",
        decay_date="2022-06-01",
    )

    insert_satcat(
        catalogue,
        object_id="c",
        norad_id=10003,
        name="C",
        object_type="DEB",
        launch_date="2010-01-01",
    )

    overlap = catalogue.objects(
        start="2021-01-01",
        end="2022-01-01",
        existence="overlap",
        object_type="payload",
    )

    assert overlap["norad_id"].tolist() == [
        10001,
        10002,
    ]

    throughout = catalogue.objects(
        start="2021-01-01",
        end="2022-01-01",
        existence="throughout",
        object_type="payload",
    )

    assert throughout["norad_id"].tolist() == [
        10001,
    ]


def test_period_objects_end_boundary():
    catalogue = LocalCatalogue()

    insert_satcat(
        catalogue,
        object_id="a",
        norad_id=10001,
        name="A",
        object_type="PAY",
        launch_date="2020-01-01",
        decay_date="2022-01-01",
    )

    rows = catalogue.objects(
        start="2021-01-01",
        end="2022-01-01",
        existence="throughout",
        object_type="payload",
    )

    assert rows["norad_id"].tolist() == [
        10001,
    ]


def test_orbit_public_interval_is_half_open():
    archive = Archive.__new__(Archive)

    archive.con = duckdb.connect(":memory:")

    archive.con.execute(
        """
        CREATE TABLE orbit_elements(
            norad_id INTEGER,
            source VARCHAR,
            epoch TIMESTAMP
        )
        """
    )

    archive.con.execute(
        """
        INSERT INTO orbit_elements
        VALUES
            (
                12345,
                'spacetrack',
                TIMESTAMP '2024-01-01 12:00:00'
            ),
            (
                12345,
                'spacetrack',
                TIMESTAMP '2024-01-02 00:00:00'
            )
        """
    )

    result = archive.orbit(
        norad_id=12345,
        start="2024-01-01",
        end="2024-01-02",
        sync=False,
    )

    assert len(result) == 1
    assert str(result.iloc[0]["epoch"]).startswith("2024-01-01")


def test_orbit_rejects_empty_interval():
    archive = Archive.__new__(Archive)

    archive.con = duckdb.connect(":memory:")

    archive.con.execute(
        """
        CREATE TABLE orbit_elements(
            norad_id INTEGER,
            source VARCHAR,
            epoch TIMESTAMP
        )
        """
    )

    with pytest.raises(
        ValueError,
        match="start must be before end",
    ):
        archive.orbit(
            norad_id=12345,
            start="2024-01-01",
            end="2024-01-01",
            sync=False,
        )


def test_celestrak_bulk_satcat_raw_extension():
    source = CelesTrakSource()

    assert (
        source.raw_extension_for(
            "satcat",
            all=True,
        )
        == "csv"
    )

    assert (
        source.raw_extension_for(
            "satcat",
            norad_id=25544,
        )
        == "json"
    )


def test_period_objects_default_is_not_truncated():
    catalogue = LocalCatalogue()

    for index in range(105):
        insert_satcat(
            catalogue,
            object_id=f"object-{index}",
            norad_id=20000 + index,
            name=f"SAT-{index}",
            object_type="PAY",
            launch_date="2020-01-01",
        )

    rows = catalogue.objects(
        start="2021-01-01",
        end="2022-01-01",
        object_type="payload",
    )

    assert len(rows) == 105


def test_bulk_satcat_request_skips_eager_identity():
    source = CelesTrakSource()

    assert not source.should_index_identity_request(
        "satcat",
        all=True,
    )

    assert source.should_index_identity_request(
        "satcat",
        norad_id=25544,
    )


def test_period_query_uses_raw_satcat_snapshot(
    tmp_path,
):
    import pandas as pd

    class SnapshotCatalogue(LocalCatalogue):
        def __init__(self):
            super().__init__()

            self.path = tmp_path / "satcat.csv"

            self.path.write_text(
                (
                    "OBJECT_NAME,OBJECT_ID,"
                    "NORAD_CAT_ID,OBJECT_TYPE,"
                    "LAUNCH_DATE,DECAY_DATE\n"
                    "ALPHA,2020-001A,"
                    "12345,PAY,"
                    "2020-01-01,\n"
                    "BRAVO,2021-001A,"
                    "12346,DEB,"
                    "2021-01-01,\n"
                ),
                encoding="utf-8",
            )

        def artifacts(
            self,
            **kwargs,
        ):
            return pd.DataFrame(
                [
                    {
                        "artifact_id": ("bulk-test"),
                        "retrieved_at": (
                            pd.Timestamp(
                                "2026-01-01",
                                tz="UTC",
                            )
                        ),
                        "path": str(self.path),
                    }
                ]
            )

        def get_source(
            self,
            name,
        ):
            assert name == "celestrak"

            return CelesTrakSource()

    catalogue = SnapshotCatalogue()

    result = catalogue.objects(
        start="2021-01-01",
        end="2022-01-01",
        existence="throughout",
        object_type="payload",
        sync=False,
    )

    assert result["norad_id"].tolist() == [12345]

    assert result.iloc[0]["catalogue_artifact_id"] == "bulk-test"

    assert catalogue.con.execute("SELECT count(*) FROM objects").fetchone()[0] == 0
