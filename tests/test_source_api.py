import pytest

from orbitoby.source_api import SourceAPI
from orbitoby.sources.base import SourceAdapter
from orbitoby.sources.gcat import GCATSource
from orbitoby.sources.nrcan import NRCanSource
from orbitoby.sources.swarm import SwarmSource


class FakeArchive(SourceAPI):
    def __init__(self):
        self.sources = {
            "gcat": GCATSource(),
        }

    def get_source(
        self,
        name,
    ):
        return self.sources[name]


class MultiSourceArchive(SourceAPI):
    def __init__(self):
        self.sources = {
            "gcat": GCATSource(),
            "nrcan": NRCanSource(),
            "swarm": SwarmSource(),
        }

    def get_source(
        self,
        name,
    ):
        try:
            return self.sources[name]
        except KeyError as exc:
            raise ValueError(f"Unknown source: {name}") from exc


class FakeLiveSource(SourceAdapter):
    name = "fake_live"
    datasets = ("series",)

    def fetch(
        self,
        dataset,
        **params,
    ):
        return b"[]"

    def normalize(
        self,
        dataset,
        payload,
        **context,
    ):
        return []

    def info(
        self,
        dataset,
    ):
        assert dataset == "series"

        return {
            "startDate": ("2001-01-01T00:00:00Z"),
            "stopDate": ("2026-01-01T00:00:00Z"),
        }


class FakeLiveArchive(SourceAPI):
    def __init__(self):
        self.sources = {
            "fake_live": FakeLiveSource(),
        }

    def get_source(
        self,
        name,
    ):
        return self.sources[name]


def test_source_info():
    archive = FakeArchive()

    info = archive.source_info("gcat")

    assert info["name"] == "gcat"
    assert info["title"] == ("General Catalog of Artificial Space Objects")


def test_credits_never_guess_citations():
    archive = FakeArchive()

    credits = archive.credits()

    assert credits[0]["name"] == "gcat"
    assert "citation" not in credits[0]


def test_licenses_preserve_unknown_policy():
    archive = FakeArchive()

    licenses = archive.licenses()

    assert licenses[0]["policy"]["redistribution"] == "unknown"


def test_source_info_preserves_adapter_datasets():
    archive = FakeArchive()

    info = archive.source_info("gcat")

    assert "satcat" in info["datasets"]

    assert "usatcat" in info["datasets"]


def test_dataset_catalogue_contains_all_adapter_datasets():
    archive = MultiSourceArchive()

    rows = archive.datasets(source="gcat")

    names = {row["dataset"] for row in rows}

    assert names == set(archive.sources["gcat"].datasets)


def test_object_catalogue_scope_is_derived_from_identity_routing():
    archive = MultiSourceArchive()

    info = archive.dataset_info(
        "gcat",
        "satcat",
    )

    assert info["object_scope"] == "catalogue"

    assert info["object_query_supported"] is True


def test_swarm_fixed_spacecraft_and_cadence_are_visible():
    archive = MultiSourceArchive()

    acc = archive.dataset_info(
        "swarm",
        "density_a_acc",
    )

    pod = archive.dataset_info(
        "swarm",
        "density_c_pod",
    )

    assert acc["object_scope"] == "fixed"
    assert acc["objects"] == ["Swarm A"]
    assert acc["cadence"] == "10 s"

    assert pod["objects"] == ["Swarm C"]
    assert pod["cadence"] == "30 s"


def test_dataset_catalogue_derives_canonical_metadata():
    archive = MultiSourceArchive()

    rows = archive.datasets(source="nrcan")

    canonical_rows = [row for row in rows if row["canonical_metrics"]]

    assert canonical_rows
    assert any(row["units"] for row in canonical_rows)


def test_dataset_info_live_provider_coverage():
    archive = FakeLiveArchive()

    info = archive.dataset_info(
        "fake_live",
        "series",
        live=True,
    )

    assert info["available_start"] == ("2001-01-01T00:00:00Z")

    assert info["available_end"] == ("2026-01-01T00:00:00Z")

    assert info["availability_source"] == "provider"


def test_datasets_live_surfaces_provider_errors():
    class BrokenSource(FakeLiveSource):
        name = "broken"

        def info(
            self,
            dataset,
        ):
            raise RuntimeError("provider unavailable")

    class BrokenArchive(SourceAPI):
        def __init__(self):
            self.sources = {
                "broken": BrokenSource(),
            }

        def get_source(
            self,
            name,
        ):
            return self.sources[name]

    row = BrokenArchive().datasets(live=True)[0]

    assert row["availability_error"].startswith("RuntimeError:")


def test_dataset_catalogue_filters_by_scope():
    archive = MultiSourceArchive()

    rows = archive.datasets(object_scope="fixed")

    assert rows
    assert {row["source"] for row in rows} == {
        "swarm",
    }


def test_dataset_info_rejects_unknown_dataset():
    archive = MultiSourceArchive()

    with pytest.raises(
        ValueError,
        match="Unknown dataset",
    ):
        archive.dataset_info(
            "nrcan",
            "does_not_exist",
        )


def test_dataset_scope_semantics():
    archive = MultiSourceArchive()

    nrcan = archive.dataset_info(
        "nrcan",
        "f107_measurements",
    )
    swarm = archive.dataset_info(
        "swarm",
        "density_a_acc",
    )
    gcat = archive.dataset_info(
        "gcat",
        "satcat",
    )

    assert nrcan["data_scope"] == "global"
    assert nrcan["object_scope"] == "none"

    assert swarm["data_scope"] == "fixed_object"
    assert swarm["object_scope"] == "fixed"

    assert gcat["data_scope"] == "object_catalogue"
    assert gcat["object_scope"] == "catalogue"


def test_dataset_catalogue_filters_by_data_scope():
    archive = MultiSourceArchive()

    rows = archive.datasets(data_scope="fixed_object")

    assert rows

    assert {row["source"] for row in rows} == {"swarm"}
