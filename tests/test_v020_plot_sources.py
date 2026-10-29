"""Contract tests for native Orbitoby PlotResult source display."""

from __future__ import annotations

import pandas as pd

from orbitoby._easy_result import DataResult


def source_result(metric: str, source: str, dataset: str, unit: str) -> DataResult:
    return DataResult(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    ["2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z"], utc=True
                ),
                "metric": [metric, metric],
                "value": [100.0, 103.0],
                "unit": [unit, unit],
                "source": [source, source],
                "dataset": [dataset, dataset],
            }
        ),
        name=metric,
        start="2024-01-01",
        end="2024-01-03",
        source=source,
    )


def test_plot_sources_exact_and_saved(tmp_path):
    a = source_result("f107_observed", "gfz", "f107", "sfu")
    b = source_result("mean_motion", "spacetrack", "gp_history", "rev/day")
    fig = a.plot(below=b)
    source_table = fig.sources().table
    assert set(source_table["source"]) == {"gfz", "spacetrack"}
    assert set(source_table["metric"]) == {"f107_observed", "mean_motion"}
    assert callable(fig.sources().open)
    saved = fig.save(tmp_path / "attributed.svg")
    assert saved.read_text(encoding="utf-8") == fig.svg
    assert "<metadata>" in fig.svg
    assert "gfz" in fig.svg.lower() and "spacetrack" in fig.svg.lower()


def test_plot_sources_defensive_copy():
    fig = source_result("kp", "gfz", "kp", "index").plot()
    copy = fig.sources().table
    assert len(copy) >= 1
    copy.loc[:, "source"] = "modified"
    assert "modified" not in set(fig.sources().table["source"])
