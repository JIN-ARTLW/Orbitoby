from __future__ import annotations

import pandas as pd
import pytest

from orbitoby.plotting import PlotAPI, PlotResult


def canonical_frame():
    return pd.DataFrame(
        [
            {
                "timestamp": "2024-05-10T17:00:00Z",
                "metric": "f107_observed",
                "value": 214.5,
                "unit": "sfu",
                "source_value": 214.5,
                "source": "nrcan",
                "dataset": "f107_measurements",
                "source_field": "f107_observed",
                "status": "unknown",
                "provider_status": None,
                "quality_flag": None,
                "artifact_kind": "measurement",
                "artifact_id": "artifact-1",
                "retrieved_at": "2026-10-01T00:00:00Z",
                "transform": "orbitoby.canonical",
                "transform_version": "1",
            },
            {
                "timestamp": "2024-05-10T20:00:00Z",
                "metric": "f107_observed",
                "value": 223.4,
                "unit": "sfu",
                "source_value": 223.4,
                "source": "nrcan",
                "dataset": "f107_measurements",
                "source_field": "f107_observed",
                "status": "unknown",
                "provider_status": None,
                "quality_flag": None,
                "artifact_kind": "measurement",
                "artifact_id": "artifact-1",
                "retrieved_at": "2026-10-01T00:00:00Z",
                "transform": "orbitoby.canonical",
                "transform_version": "1",
            },
        ]
    )


def test_plot_rejects_noncanonical_frame():
    api = PlotAPI()
    with pytest.raises(ValueError, match="required column"):
        api.plot(pd.DataFrame({"x": [1], "y": [2]}))


def test_plot_rejects_empty_frame():
    api = PlotAPI()
    with pytest.raises(ValueError, match="empty"):
        api.plot(
            pd.DataFrame(
                columns=[
                    "timestamp",
                    "metric",
                    "value",
                    "unit",
                    "source",
                    "dataset",
                ]
            )
        )


def test_plot_rejects_mixed_units():
    api = PlotAPI()
    frame = canonical_frame()
    second = frame.iloc[[0]].copy()
    second["metric"] = "kp"
    second["unit"] = "1"
    mixed = pd.concat([frame, second], ignore_index=True)
    with pytest.raises(ValueError, match="different units"):
        api.plot(mixed)


def test_native_line_svg():
    api = PlotAPI()
    result = api.plot(canonical_frame(), kind="line")
    assert isinstance(result, PlotResult)
    assert result.svg.startswith("<svg")
    assert "<polyline" in result.svg
    assert "matplotlib" not in result.svg
    assert result._repr_svg_() == result.svg
    assert result.provenance.iloc[0]["artifact_id"] == "artifact-1"


def test_native_scatter_svg():
    api = PlotAPI()
    result = api.plot(canonical_frame(), kind="scatter")
    assert "<circle" in result.svg


def test_missing_value_breaks_line():
    api = PlotAPI()
    frame = canonical_frame()
    middle = frame.iloc[[0]].copy()
    middle["timestamp"] = "2024-05-10T18:30:00Z"
    middle["value"] = None
    frame = pd.concat(
        [frame.iloc[[0]], middle, frame.iloc[[1]]],
        ignore_index=True,
    )
    result = api.plot(frame, kind="line")
    assert "<polyline" not in result.svg
    assert result.svg.count("<circle") == 2


def test_plot_save_svg(tmp_path):
    api = PlotAPI()
    result = api.plot(canonical_frame())
    target = tmp_path / "quicklook.svg"
    returned = result.save(target)
    assert returned == target
    assert target.read_text(encoding="utf-8") == result.svg


def test_plot_save_rejects_non_svg(tmp_path):
    api = PlotAPI()
    result = api.plot(canonical_frame())
    with pytest.raises(ValueError, match=r"\.svg"):
        result.save(tmp_path / "plot.png")


def test_no_plottable_values():
    api = PlotAPI()
    frame = canonical_frame()
    frame["value"] = None
    with pytest.raises(ValueError, match="no plottable"):
        api.plot(frame)
