import pandas as pd
import pytest

import orbitoby as ob
from orbitoby._easy_result import DataResult

START = "2024-05-10"
END = "2024-05-11"


def make_result(name, frame):
    return DataResult(
        frame,
        name=name,
        start=START,
        end=END,
        source=name,
    )


def test_exact_union_does_not_interpolate():
    kp = make_result(
        "gfz",
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    [
                        "2024-05-10T00:00:00Z",
                        "2024-05-10T03:00:00Z",
                    ],
                    utc=True,
                ),
                "metric": ["kp", "kp"],
                "source": ["gfz", "gfz"],
                "dataset": ["kp", "kp"],
                "value": [2.0, 3.0],
                "unit": ["1", "1"],
            }
        ),
    )

    dst = make_result(
        "kyoto",
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    [
                        "2024-05-10T01:00:00Z",
                    ],
                    utc=True,
                ),
                "metric": ["dst"],
                "source": ["wdc_kyoto"],
                "dataset": ["dst"],
                "value": [-80.0],
                "unit": ["nT"],
            }
        ),
    )

    aligned = ob.study(START, END).align(kp, dst)

    assert len(aligned.table) == 3
    assert len(aligned.provenance) == 3
    assert len(aligned.series_info) == 2

    assert aligned.presence.iloc[:, 1:].sum().sum() == 3
    assert aligned.table.iloc[:, 1:].isna().sum().sum() == 3


def test_multiple_satellites_remain_separate():
    orbit = make_result(
        "spacetrack",
        pd.DataFrame(
            {
                "EPOCH": pd.to_datetime(
                    [
                        "2024-05-10T00:00:00Z",
                        "2024-05-10T00:00:00Z",
                    ],
                    utc=True,
                ),
                "NORAD_CAT_ID": [39452, 39451],
                "source": ["spacetrack", "spacetrack"],
                "dataset": ["gp_history", "gp_history"],
                "INCLINATION": [87.0, 87.5],
            }
        ),
    )

    weather = make_result(
        "gfz",
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-05-10T00:00:00Z"], utc=True),
                "metric": ["kp"],
                "source": ["gfz"],
                "dataset": ["kp"],
                "value": [2.0],
                "unit": ["1"],
            }
        ),
    )

    aligned = ob.study(START, END).align(weather, orbit)

    assert len(aligned.table) == 1
    assert len(aligned.series_info) == 3
    assert len(aligned.provenance) == 3

    orbit_series = [
        spec
        for spec in aligned.series_info.values()
        if spec["representation"] == "record count"
    ]

    assert {spec["norad_id"] for spec in orbit_series} == {"39452", "39451"}

    # Orbit element values remain unchanged in original provenance.
    assert sorted(aligned.provenance["INCLINATION"].dropna().tolist()) == [87.0, 87.5]

    for label, spec in aligned.series_info.items():
        if spec["representation"] == "record count":
            assert aligned.table.loc[0, label] == 1
            assert bool(aligned.presence.loc[0, label])


def test_ambiguous_duplicate_series_is_rejected():
    repeated = make_result(
        "gfz",
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    ["2024-05-10T00:00:00Z"] * 2,
                    utc=True,
                ),
                "metric": ["kp", "kp"],
                "source": ["gfz", "gfz"],
                "dataset": ["kp", "kp"],
                "value": [2.0, 3.0],
                "unit": ["1", "1"],
            }
        ),
    )

    single = make_result(
        "kyoto",
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    ["2024-05-10T00:00:00Z"],
                    utc=True,
                ),
                "metric": ["dst"],
                "source": ["wdc_kyoto"],
                "dataset": ["dst"],
                "value": [-80.0],
                "unit": ["nT"],
            }
        ),
    )

    with pytest.raises(ValueError, match="Duplicate records"):
        ob.study(START, END).align(repeated, single)


def test_alignment_export_keeps_private_context_out(tmp_path):
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-05-10T00:00:00Z"], utc=True),
            "metric": ["kp"],
            "source": ["gfz"],
            "dataset": ["kp"],
            "value": [2.0],
            "unit": ["1"],
            "context": [{"secret": "DO_NOT_EXPORT"}],
        }
    )

    a = make_result("a", frame)
    b = make_result("b", frame)

    aligned = ob.study(START, END).align(a, b)
    path = aligned.save(tmp_path / "research.csv")

    assert path.exists()
    assert (tmp_path / "research_presence.csv").exists()
    assert (tmp_path / "research_missing.csv").exists()
    assert (tmp_path / "research_provenance.csv").exists()
    assert (tmp_path / "research_metadata.json").exists()

    assert "DO_NOT_EXPORT" not in (tmp_path / "research_provenance.csv").read_text()
