import pandas as pd
import pytest

from orbitoby.research import (
    ResearchAPI,
    ResearchWindow,
)


def canonical_rows():
    return pd.DataFrame(
        [
            {
                "timestamp": pd.Timestamp("2024-01-01T00:00:00Z"),
                "metric": "kp",
                "value": 3.0,
                "unit": "1",
                "source": "gfz",
                "dataset": "kp",
                "artifact_id": "a",
                "is_missing": False,
                "missing_reason": None,
            },
            {
                "timestamp": pd.Timestamp("2024-01-01T03:00:00Z"),
                "metric": "kp",
                "value": None,
                "unit": "1",
                "source": "gfz",
                "dataset": "kp",
                "artifact_id": "a",
                "is_missing": True,
                "missing_reason": ("provider_fill"),
            },
            {
                "timestamp": pd.Timestamp("2024-01-01T00:00:00Z"),
                "metric": "dst",
                "value": -20.0,
                "unit": "nT",
                "source": "wdc_kyoto",
                "dataset": "dst_hourly",
                "artifact_id": "b",
                "is_missing": False,
                "missing_reason": None,
            },
            {
                "timestamp": pd.Timestamp("2024-01-01T06:00:00Z"),
                "metric": "dst",
                "value": -30.0,
                "unit": "nT",
                "source": "wdc_kyoto",
                "dataset": "dst_hourly",
                "artifact_id": "b",
                "is_missing": False,
                "missing_reason": None,
            },
        ]
    )


class WindowArchive(ResearchAPI):
    def __init__(
        self,
        result=None,
    ):
        self.result = canonical_rows() if result is None else result
        self.calls = []

    def timeseries(
        self,
        **kwargs,
    ):
        self.calls.append(kwargs)

        return self.result.copy()


def test_window_exact_outer_alignment():
    archive = WindowArchive()

    result = archive.window(
        start="2024-01-01",
        end="2024-01-02",
        fields=[
            "kp",
            "dst",
        ],
    )

    assert isinstance(
        result,
        ResearchWindow,
    )

    assert result.data["timestamp"].tolist() == list(
        pd.to_datetime(
            [
                "2024-01-01T00:00:00Z",
                "2024-01-01T03:00:00Z",
                "2024-01-01T06:00:00Z",
            ],
            utc=True,
        )
    )

    assert list(result.data.columns) == [
        "timestamp",
        "kp",
        "dst",
    ]


def test_window_does_not_interpolate():
    result = WindowArchive().window(
        start="2024-01-01",
        end="2024-01-02",
        fields=[
            "kp",
            "dst",
        ],
    )

    assert len(result.data) == 3

    # dst has no real row at 03:00.
    row = result.data[
        result.data["timestamp"] == pd.Timestamp("2024-01-01T03:00:00Z")
    ].iloc[0]

    assert pd.isna(row["dst"])


def test_window_distinguishes_absence_from_provider_missing():
    result = WindowArchive().window(
        start="2024-01-01",
        end="2024-01-02",
        fields=[
            "kp",
            "dst",
        ],
    )

    at_03 = result.presence[
        result.presence["timestamp"] == pd.Timestamp("2024-01-01T03:00:00Z")
    ].iloc[0]

    assert bool(at_03["kp"])

    assert not bool(at_03["dst"])

    missing = result.missing_reason[
        result.missing_reason["timestamp"] == pd.Timestamp("2024-01-01T03:00:00Z")
    ].iloc[0]

    assert missing["kp"] == "provider_fill"

    assert pd.isna(missing["dst"])


def test_window_preserves_provenance():
    result = WindowArchive().window(
        start="2024-01-01",
        end="2024-01-02",
        fields=[
            "kp",
            "dst",
        ],
    )

    assert len(result.provenance) == 4

    assert set(result.provenance["artifact_id"]) == {
        "a",
        "b",
    }

    assert result.units == {
        "kp": "1",
        "dst": "nT",
    }


def test_window_rejects_duplicate_metric_timestamp():
    data = canonical_rows()

    duplicate = data.iloc[[0]].copy()

    duplicate["artifact_id"] = "second-artifact"

    archive = WindowArchive(
        pd.concat(
            [
                data,
                duplicate,
            ],
            ignore_index=True,
        )
    )

    with pytest.raises(
        ValueError,
        match="exactly one canonical row",
    ):
        archive.window(
            start="2024-01-01",
            end="2024-01-02",
            fields=["kp", "dst"],
        )


def test_window_rejects_unit_conflict():
    data = canonical_rows()

    extra = data.iloc[[0]].copy()

    extra["timestamp"] = pd.Timestamp("2024-01-01T09:00:00Z")

    extra["unit"] = "nT"

    archive = WindowArchive(
        pd.concat(
            [
                data,
                extra,
            ],
            ignore_index=True,
        )
    )

    with pytest.raises(
        ValueError,
        match="multiple units",
    ):
        archive.window(
            start="2024-01-01",
            end="2024-01-02",
            fields=["kp", "dst"],
        )


def test_window_to_numpy():
    result = WindowArchive().window(
        start="2024-01-01",
        end="2024-01-02",
        fields=[
            "kp",
            "dst",
        ],
    )

    values = result.to_numpy()

    assert values.shape == (
        3,
        2,
    )


def test_window_empty_result():
    empty = canonical_rows().iloc[0:0].copy()

    result = WindowArchive(empty).window(
        start="2024-01-01",
        end="2024-01-02",
        fields=[
            "kp",
            "dst",
        ],
    )

    assert result.data.empty

    assert list(result.data.columns) == [
        "timestamp",
        "kp",
        "dst",
    ]
