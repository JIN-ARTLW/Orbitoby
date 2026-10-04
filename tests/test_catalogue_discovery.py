from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pytest

from orbitoby.archive.raw import RawArtifact
from orbitoby.catalogue import CatalogueAPI
from orbitoby.sources.gcat import GCATSource
from orbitoby.warehouse.identity import (
    SCHEMA,
    IdentityStore,
)


class CatalogueArchive(CatalogueAPI):
    def __init__(self):
        self.con = duckdb.connect(":memory:")
        self.con.execute(SCHEMA)
        self.sources = {
            "gcat": GCATSource(),
        }

    def get_source(
        self,
        name,
    ):
        try:
            return self.sources[name]
        except KeyError as exc:
            raise ValueError(f"Unknown source: {name}") from exc


def artifact():
    return RawArtifact(
        artifact_id="catalogue-discovery-test",
        source="gcat",
        dataset="satcat",
        norad_id=None,
        requested_start=None,
        requested_end=None,
        retrieved_at=datetime(
            2026,
            1,
            1,
            tzinfo=UTC,
        ),
        sha256="0" * 64,
        path=Path("/tmp/catalogue-test.tsv"),
    )


def populated_archive():
    archive = CatalogueArchive()

    IdentityStore(archive.con).ingest(
        [
            {
                "JCAT": "S00001",
                "Satcat": "25544",
                "Piece": "1998-067A",
                "Name": ("International Space Station"),
                "Mass": "420000",
                "State": "US",
                "Status": "O",
            },
            {
                "JCAT": "S00002",
                "Satcat": "20580",
                "Piece": "1990-037B",
                "Name": ("Hubble Space Telescope"),
                "Mass": "11110",
                "State": "US",
                "Status": "O",
            },
        ],
        artifact(),
    )

    return archive


def test_objects_searches_by_name():
    archive = populated_archive()

    result = archive.objects(search="space station")

    assert len(result) == 1
    assert result.iloc[0]["norad_id"] == 25544


def test_objects_searches_by_norad():
    archive = populated_archive()

    result = archive.objects(norad_id=20580)

    assert len(result) == 1
    assert result.iloc[0]["cospar_id"] == "1990-037B"


def test_objects_searches_by_cospar():
    archive = populated_archive()

    result = archive.objects(cospar_id="1998-067A")

    assert len(result) == 1
    assert result.iloc[0]["norad_id"] == 25544


def test_objects_filters_source_and_dataset():
    archive = populated_archive()

    result = archive.objects(
        source="gcat",
        dataset="satcat",
        search="Hubble",
    )

    assert len(result) == 1
    assert result.iloc[0]["norad_id"] == 20580


def test_objects_supports_property_filtering():
    archive = populated_archive()

    result = archive.objects(
        properties={
            "mass_kg": (
                ">",
                100000,
            ),
        }
    )

    assert len(result) == 1
    assert result.iloc[0]["norad_id"] == 25544


def test_objects_rejects_empty_search():
    archive = populated_archive()

    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        archive.objects(search="   ")


def test_objects_rejects_non_object_dataset():
    archive = populated_archive()

    archive.sources["gcat"].identity_datasets = frozenset()

    with pytest.raises(
        ValueError,
        match="not an object-catalogue",
    ):
        archive.objects(
            source="gcat",
            dataset="satcat",
        )


def test_object_detail_preserves_provider_record():
    archive = populated_archive()

    result = archive.object(norad_id=25544)

    assert result is not None
    assert result["norad_id"] == 25544

    assert result["source_records"]

    assert result["source_records"][0]["data"]["Name"] == (
        "International Space Station"
    )
