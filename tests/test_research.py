from datetime import UTC, datetime
from pathlib import Path

import pytest

from orbitoby.archive.raw import RawArtifact
from orbitoby.research import ResearchAPI


class FakeArchive(ResearchAPI):
    def __init__(
        self,
        responses,
    ):
        self.responses = responses

    def _fetch_records(
        self,
        *,
        source,
        dataset,
        archive_raw=True,
        **params,
    ):
        del archive_raw
        del params

        records = self.responses.get(
            (
                source,
                dataset,
            ),
            [],
        )

        artifact = RawArtifact(
            artifact_id=(f"artifact-{dataset}"),
            source=source,
            dataset=dataset,
            norad_id=None,
            requested_start=None,
            requested_end=None,
            retrieved_at=datetime(
                2026,
                10,
                1,
                tzinfo=UTC,
            ),
            sha256="0" * 64,
            path=Path("/tmp/fake"),
        )

        return records, artifact


def test_timeseries_canonical_frame():
    archive = FakeArchive(
        {
            (
                "nrcan",
                "f107_measurements",
            ): [
                {
                    "time": ("2024-05-10T17:00:00Z"),
                    "f107_observed": 214.5,
                }
            ]
        }
    )

    frame = archive.timeseries(
        "f107_observed",
        start="2024-05-10",
        end="2024-05-11",
        source="nrcan",
    )

    assert len(frame) == 1

    row = frame.iloc[0]

    assert row["value"] == 214.5
    assert row["source"] == "nrcan"


def test_space_weather_prefix():
    archive = FakeArchive(
        {
            (
                "nrcan",
                "f107_measurements",
            ): [
                {
                    "time": ("2024-05-10T17:00:00Z"),
                    "f107_observed": 214.5,
                }
            ]
        }
    )

    frame = archive.space_weather(
        start="2024-05-10",
        end="2024-05-11",
        fields=("space_weather.f107_observed"),
        source="nrcan",
    )

    assert len(frame) == 1


def test_overlapping_artifacts_preserved():
    timestamp = "2005-01-01T17:00:00Z"

    archive = FakeArchive(
        {
            (
                "nrcan",
                "f107_measurements",
            ): [
                {
                    "time": timestamp,
                    "f107_observed": 100.0,
                }
            ],
            (
                "nrcan",
                ("f107_legacy_measurements_1996_2007"),
            ): [
                {
                    "time": timestamp,
                    "f107_observed": 99.0,
                }
            ],
        }
    )

    frame = archive.timeseries(
        "f107_observed",
        start="2005-01-01",
        end="2005-01-02",
        source="nrcan",
    )

    assert set(frame["value"]) == {
        99.0,
        100.0,
    }


def test_preferred_is_explicit():
    timestamp = "2005-01-01T17:00:00Z"

    archive = FakeArchive(
        {
            (
                "nrcan",
                "f107_measurements",
            ): [
                {
                    "time": timestamp,
                    "f107_observed": 100.0,
                }
            ],
            (
                "nrcan",
                ("f107_legacy_measurements_1996_2007"),
            ): [
                {
                    "time": timestamp,
                    "f107_observed": 99.0,
                }
            ],
        }
    )

    frame = archive.timeseries(
        "f107_observed",
        start="2005-01-01",
        end="2005-01-02",
        source="nrcan",
        artifact_resolution=("preferred"),
    )

    assert len(frame) == 1

    assert frame.iloc[0]["value"] == 100.0


def test_swarm_requires_dataset():
    archive = FakeArchive({})

    with pytest.raises(
        ValueError,
        match="non-mergeable",
    ):
        archive.timeseries(
            ("thermosphere_neutral_mass_density"),
            start="2015-04-01",
            end="2015-04-02",
            source="swarm",
        )


class CountingArchive(FakeArchive):
    def __init__(
        self,
        responses,
    ):
        super().__init__(responses)
        self.calls = []

    def _fetch_records(
        self,
        *,
        source,
        dataset,
        archive_raw=True,
        **params,
    ):
        self.calls.append(
            (
                source,
                dataset,
            )
        )

        return super()._fetch_records(
            source=source,
            dataset=dataset,
            archive_raw=(archive_raw),
            **params,
        )


def test_same_dataset_is_fetched_once():
    archive = CountingArchive(
        {
            (
                "cdaweb",
                "omni_hourly",
            ): [
                {
                    "Time": ("2024-05-10T00:00:00Z"),
                    "V1800": 420.0,
                    "N1800": 5.2,
                }
            ]
        }
    )

    frame = archive.timeseries(
        fields=[
            "solar_wind_speed",
            ("solar_wind_proton_density"),
        ],
        source="cdaweb",
        start="2024-05-10",
        end="2024-05-11",
    )

    assert len(frame) == 2

    assert archive.calls == [
        (
            "cdaweb",
            "omni_hourly",
        )
    ]


def test_empty_timeseries_schema_includes_method():
    class EmptyArchive(ResearchAPI):
        def _fetch_records(
            self,
            *,
            source,
            dataset,
            archive_raw=True,
            **params,
        ):
            return [], None

    archive = EmptyArchive()

    result = archive.timeseries(
        "kp",
        source="gfz",
        dataset="kp",
        start="2024-01-01",
        end="2024-01-02",
    )

    assert result.empty
    assert "method" in result.columns
