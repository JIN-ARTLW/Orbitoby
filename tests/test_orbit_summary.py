import pandas as pd

from orbitoby.service import Archive


def orbit_frame(
    *,
    norad_id,
    epochs,
    periapsis,
    apoapsis=None,
    inclination=None,
    eccentricity=None,
    mean_motion=None,
    artifacts=None,
):
    count = len(epochs)

    def values(
        value,
        default,
    ):
        if value is None:
            return [default] * count

        return value

    return pd.DataFrame(
        {
            "norad_id": [norad_id] * count,
            "epoch": epochs,
            "periapsis_km": periapsis,
            "apoapsis_km": values(
                apoapsis,
                500.0,
            ),
            "inclination_deg": values(
                inclination,
                50.0,
            ),
            "eccentricity": values(
                eccentricity,
                0.001,
            ),
            "mean_motion": values(
                mean_motion,
                15.0,
            ),
            "source": ["spacetrack"] * count,
            "artifact_id": (
                artifacts if artifacts is not None else ["artifact-a"] * count
            ),
        }
    )


class FakeArchive(Archive):
    def __init__(
        self,
        frames,
        errors=None,
    ):
        self.frames = frames
        self.errors = errors or {}
        self.calls = []

    def orbit(
        self,
        *,
        norad_id,
        start,
        end,
        source="spacetrack",
        sync=True,
    ):
        self.calls.append(
            {
                "norad_id": norad_id,
                "start": start,
                "end": end,
                "source": source,
                "sync": sync,
            }
        )

        if norad_id in self.errors:
            raise self.errors[norad_id]

        return self.frames.get(
            norad_id,
            pd.DataFrame(),
        ).copy()


def test_orbit_summary_accepts_candidates_dataframe():
    archive = FakeArchive(
        {
            10001: orbit_frame(
                norad_id=10001,
                epochs=[
                    "2024-01-01T12:00:00Z",
                    "2024-01-02T12:00:00Z",
                    "2024-01-03T12:00:00Z",
                ],
                periapsis=[
                    400.0,
                    390.0,
                    380.0,
                ],
                artifacts=[
                    "artifact-a",
                    "artifact-a",
                    "artifact-b",
                ],
            ),
            10002: orbit_frame(
                norad_id=10002,
                epochs=[
                    "2024-01-01T12:00:00Z",
                    "2024-01-02T12:00:00Z",
                    "2024-01-03T12:00:00Z",
                ],
                periapsis=[
                    800.0,
                    790.0,
                    780.0,
                ],
            ),
        }
    )

    candidates = pd.DataFrame(
        {
            "norad_id": [
                10001,
                10002,
            ],
            "name": [
                "LOW",
                "HIGH",
            ],
        }
    )

    result = archive.orbit_summary(
        candidates,
        start="2024-01-01",
        end="2024-01-04",
        periapsis_km=(
            300,
            700,
        ),
        min_coverage=1.0,
        sync=False,
    )

    assert result["norad_id"].tolist() == [
        10001,
        10002,
    ]

    assert result["name"].tolist() == [
        "LOW",
        "HIGH",
    ]

    assert result["matches"].tolist() == [
        True,
        False,
    ]

    assert result.iloc[0]["artifact_count"] == 2

    assert result.iloc[0]["periapsis_km_median"] == 390.0

    assert result.iloc[1]["filter_reason"] == "out_of_range"


def test_orbit_summary_all_vs_any():
    frame = orbit_frame(
        norad_id=10001,
        epochs=[
            "2024-01-01T12:00:00Z",
            "2024-01-02T12:00:00Z",
        ],
        periapsis=[
            400.0,
            900.0,
        ],
    )

    archive = FakeArchive(
        {
            10001: frame,
        }
    )

    all_result = archive.orbit_summary(
        [10001],
        start="2024-01-01",
        end="2024-01-03",
        periapsis_km=(
            300,
            700,
        ),
        orbit_match="all",
    )

    any_result = archive.orbit_summary(
        [10001],
        start="2024-01-01",
        end="2024-01-03",
        periapsis_km=(
            300,
            700,
        ),
        orbit_match="any",
    )

    assert not bool(all_result.iloc[0]["matches"])

    assert bool(any_result.iloc[0]["matches"])


def test_orbit_summary_coverage_is_actual_records():
    archive = FakeArchive(
        {
            10001: orbit_frame(
                norad_id=10001,
                epochs=[
                    "2024-01-01T12:00:00Z",
                    "2024-01-03T12:00:00Z",
                ],
                periapsis=[
                    400.0,
                    390.0,
                ],
            )
        }
    )

    result = archive.orbit_summary(
        [10001],
        start="2024-01-01",
        end="2024-01-05",
        min_coverage=0.75,
    )

    row = result.iloc[0]

    assert row["orbit_days"] == 2

    assert row["observed_day_ratio"] == 0.5

    assert not bool(row["matches"])

    assert row["filter_reason"] == "coverage_below_min"


def test_orbit_summary_failure_is_isolated():
    archive = FakeArchive(
        {
            10001: orbit_frame(
                norad_id=10001,
                epochs=[
                    "2024-01-01T12:00:00Z",
                ],
                periapsis=[
                    400.0,
                ],
            )
        },
        errors={
            10002: RuntimeError("provider failed"),
        },
    )

    result = archive.orbit_summary(
        [
            10001,
            10002,
        ],
        start="2024-01-01",
        end="2024-01-02",
    )

    assert len(result) == 2

    good = result[result["norad_id"] == 10001].iloc[0]

    bad = result[result["norad_id"] == 10002].iloc[0]

    assert bool(good["matches"])

    assert not bool(bad["matches"])

    assert bad["filter_reason"] == "fetch_error"

    assert "provider failed" in bad["error"]


def test_orbit_summary_defensively_enforces_half_open_interval():
    archive = FakeArchive(
        {
            10001: orbit_frame(
                norad_id=10001,
                epochs=[
                    "2024-01-01T12:00:00Z",
                    "2024-01-02T00:00:00Z",
                ],
                periapsis=[
                    400.0,
                    999.0,
                ],
            )
        }
    )

    result = archive.orbit_summary(
        [10001],
        start="2024-01-01",
        end="2024-01-02",
        periapsis_km=(
            300,
            700,
        ),
        orbit_match="all",
    )

    row = result.iloc[0]

    assert row["orbit_rows"] == 1

    assert bool(row["matches"])


def test_orbit_summary_missing_filter_data_is_explicit():
    frame = orbit_frame(
        norad_id=10001,
        epochs=[
            "2024-01-01T12:00:00Z",
            "2024-01-02T12:00:00Z",
        ],
        periapsis=[
            400.0,
            None,
        ],
    )

    archive = FakeArchive(
        {
            10001: frame,
        }
    )

    result = archive.orbit_summary(
        [10001],
        start="2024-01-01",
        end="2024-01-03",
        periapsis_km=(
            300,
            700,
        ),
        orbit_match="all",
    )

    row = result.iloc[0]

    assert not bool(row["matches"])

    assert row["filter_reason"] == "missing_filter_data"


def test_orbit_summary_rejects_boolean_norad_id():
    import pytest

    archive = FakeArchive({})

    with pytest.raises(
        TypeError,
        match="NORAD ID must not be a boolean",
    ):
        archive.orbit_summary(
            [True],
            start="2024-01-01",
            end="2024-01-02",
        )
