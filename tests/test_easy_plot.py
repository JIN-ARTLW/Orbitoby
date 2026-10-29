from xml.etree import ElementTree

import pandas as pd
import pytest

from orbitoby._easy_result import DataResult


def sample_result():
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-05-10T00:00:00Z"] * 3, utc=True),
            "metric": ["f107_observed", "kp", "dst"],
            "value": [223.4, 2.667, 12.0],
            "unit": ["sfu", "1", "nT"],
            "source": ["gfz", "gfz", "wdc_kyoto"],
            "dataset": ["f107_observed", "kp", "dst_hourly"],
            "retrieved_at": ["2026-10-03T00:00:00Z"] * 3,
        }
    )

    return DataResult(
        frame,
        name="space weather",
        start="2024-05-10",
        end="2024-05-11",
        source="recommended",
    )


def test_plot_has_separate_panels_and_sources():
    plot = sample_result().plot()

    root = ElementTree.fromstring(plot.svg)

    assert root.tag.endswith("svg")
    assert plot.svg.count('role="img"') == 4

    assert "f107_observed" in plot.svg
    assert "Kakioka" in plot.svg
    assert "13 contributing geomagnetic observatories" in plot.svg


def test_plot_has_public_links(tmp_path):
    plot = sample_result().plot()
    path = plot.save(tmp_path / "weather.svg")

    content = path.read_text()

    assert "https://kp.gfz.de/en/data" in content
    assert "https://wdc.kugi.kyoto-u.ac.jp/dstdir/" in content
    assert "<metadata>" in content


def test_plot_does_not_export_secret_context():
    result = sample_result()

    result._frame["context"] = "https://private.example/data?token=SECRET"

    assert "SECRET" not in result.plot().svg


def test_noncanonical_table_is_not_plotted():
    result = DataResult(
        pd.DataFrame({"norad_id": [39452]}),
        name="satellites",
        start="2024-05-10",
        end="2024-05-11",
        source="celestrak",
    )

    with pytest.raises(ValueError, match="not a canonical time series"):
        result.plot()


def test_shared_study_time_axis_and_full_provenance():
    result = sample_result()
    result._frame["artifact_id"] = ["a1", "a2", "a3"]
    result._frame["context"] = "private-token-123"

    plot = result.plot()

    # A single-point metric must not zoom outside the study period.
    assert "05-09" not in plot.svg

    # The plot result keeps complete scientific lineage.
    assert "artifact_id" in plot.provenance.columns
    assert "context" in plot.provenance.columns
    assert len(plot.provenance) == len(result.table)

    # Private context is not embedded in the SVG.
    assert "private-token-123" not in plot.svg


def test_window_plot_uses_requested_metric_order():
    from orbitoby._easy_result import WindowResult
    from orbitoby.research import ResearchWindow

    frame = sample_result().table
    reordered = frame.iloc[[2, 0, 1]].reset_index(drop=True)
    timestamp = frame["timestamp"].iloc[0]

    window = ResearchWindow(
        data=pd.DataFrame(
            {
                "timestamp": [timestamp],
                "f107_observed": [223.4],
                "kp": [2.667],
                "dst": [12.0],
            }
        ),
        presence=pd.DataFrame(),
        missing_reason=pd.DataFrame(),
        provenance=reordered,
        units={"f107_observed": "sfu", "kp": "1", "dst": "nT"},
    )

    result = WindowResult(
        window,
        name="space weather",
        start="2024-05-10",
        end="2024-05-11",
        source="recommended",
    )

    svg = result.plot().svg

    assert (
        svg.index("<title>f107_observed</title>")
        < svg.index("<title>kp</title>")
        < svg.index("<title>dst</title>")
    )


def test_auto_plot_does_not_connect_kp_samples():
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2024-05-10T00:00:00Z",
                    "2024-05-10T03:00:00Z",
                ],
                utc=True,
            ),
            "metric": ["kp", "kp"],
            "value": [2.0, 5.0],
            "unit": ["1", "1"],
            "source": ["gfz", "gfz"],
            "dataset": ["kp", "kp"],
        }
    )

    result = DataResult(
        frame,
        name="kp",
        start="2024-05-10",
        end="2024-05-11",
        source="gfz",
    )

    automatic = result.plot()
    explicit_line = result.plot(kind="line")

    assert automatic.svg.count('r="3.5"') == 2
    assert explicit_line.svg.count('r="3.5"') == 0
    assert automatic.provenance.equals(result.table)


def test_weather_plot_below_satellite_density():
    weather = sample_result()

    density = DataResult(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-05-10T12:00:00Z"], utc=True),
                "metric": ["thermosphere_neutral_mass_density"],
                "value": [1e-12],
                "unit": ["kg/m3"],
                "source": ["swarm"],
                "dataset": ["density_a_pod"],
                "artifact_id": ["swarm-artifact-1"],
            }
        ),
        name="Swarm A POD density",
        start="2024-05-10",
        end="2024-05-11",
        source="swarm",
    )

    plot = weather.plot(below=density)

    assert len(plot.data) == 4
    assert len(plot.provenance) == 4
    assert "swarm-artifact-1" in plot.provenance["artifact_id"].tolist()

    assert plot.svg.index("<title>dst</title>") < plot.svg.index(
        "<title>thermosphere_neutral_mass_density</title>"
    )


def test_plot_below_requires_same_period():
    weather = sample_result()

    density = DataResult(
        pd.DataFrame({"value": [1.0]}),
        name="density",
        start="2024-05-09",
        end="2024-05-11",
        source="swarm",
    )

    with pytest.raises(ValueError, match="same study period"):
        weather.plot(below=density)
