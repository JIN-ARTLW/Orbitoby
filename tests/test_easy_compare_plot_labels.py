import pandas as pd

from orbitoby._easy_result import DataResult


def make_result(values, *, source, dataset):
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2024-05-10T00:00:00Z", "2024-05-10T00:00:30Z"],
                utc=True,
            ),
            "metric": ["thermosphere_neutral_mass_density"] * 2,
            "value": values,
            "unit": ["kg/m^3"] * 2,
            "source": [source] * 2,
            "dataset": [dataset] * 2,
            "artifact_kind": [
                "provider_derived" if source == "swarm" else "model_output"
            ]
            * 2,
        }
    )
    return DataResult(
        frame,
        name=source,
        start="2024-05-10",
        end="2024-05-11",
        source=source,
    )


def test_compare_plot_legend_is_distinguishable():
    observed = make_result(
        [1.0e-12, 1.1e-12],
        source="swarm",
        dataset="density_a_pod",
    )
    modeled = make_result(
        [0.9e-12, 1.0e-12],
        source="orbitoby",
        dataset="nrlmsis_2_1_density",
    )

    comparison = observed.compare(modeled)
    svg = comparison.plot().svg

    assert "[swarm / density_a_pod]" in svg
    assert "[orbitoby / nrlmsis_2_1_density]" in svg


def test_compare_plot_scientific_axis_style():
    observed = make_result(
        [1.0e-12, 1.1e-12],
        source="swarm",
        dataset="density_a_pod",
    )
    modeled = make_result(
        [0.9e-12, 1.0e-12],
        source="orbitoby",
        dataset="nrlmsis_2_1_density",
    )

    svg = observed.compare(modeled).plot().svg

    assert "× 10⁻¹²" in svg


def test_plot_preserves_complete_source_metadata():
    import json
    from xml.etree import ElementTree as ET

    observed = make_result(
        [1.0e-12, 1.1e-12],
        source="swarm",
        dataset="density_a_pod",
    )
    modeled = make_result(
        [0.9e-12, 1.0e-12],
        source="orbitoby",
        dataset="nrlmsis_2_1_density",
    )

    figure = observed.compare(modeled).plot()
    root = ET.fromstring(figure.svg)

    ns = "{http://www.w3.org/2000/svg}"
    metadata = root.find(f"{ns}metadata")

    assert metadata is not None
    public = json.loads(metadata.text)

    assert "sources" in public
    datasets = {row["dataset"] for row in public["sources"]}
    assert "density_a_pod" in datasets
    assert "nrlmsis_2_1_density" in datasets

    visible = " ".join(node.text or "" for node in root.iter(f"{ns}text"))
    assert "density_a_pod" in visible
    assert "nrlmsis_2_1_density" in visible


def test_all_sources_visible_with_matching_references(monkeypatch):
    import json
    from xml.etree import ElementTree as ET

    observed = make_result(
        [1e-12, 1.1e-12],
        source="swarm",
        dataset="density_a_pod",
    )
    modeled = make_result(
        [0.9e-12, 1e-12],
        source="orbitoby",
        dataset="nrlmsis_2_1_density",
    )

    comparison = observed.compare(modeled)
    sources = comparison.sources()

    # Simulate an additional upstream model driver.
    extra = sources.table.iloc[[0]].copy()
    extra.loc[:, "metric"] = "daily Ap"
    extra.loc[:, "source"] = "gfz"
    extra.loc[:, "dataset"] = "ap_daily"
    extra.loc[:, "provider"] = "GFZ"

    sources._table = pd.concat([sources.table, extra], ignore_index=True)
    monkeypatch.setattr(comparison, "sources", lambda: sources)

    figure = comparison.plot()
    root = ET.fromstring(figure.svg)

    ns = "{http://www.w3.org/2000/svg}"
    metadata = json.loads(root.find(f"{ns}metadata").text)

    # All sources remain present in the SVG, not just plotted data.
    assert len(metadata["sources"]) == 3
    assert {item["source_ref"] for item in metadata["sources"]} == {"S1", "S2", "S3"}

    assert "[S1]" in figure.svg
    assert "[S2]" in figure.svg
    assert "[S3]" in figure.svg
    assert "daily Ap" in figure.svg
    assert "GFZ" in figure.svg

    # The upstream forcing isn't silently plotted as another series.
    assert len(figure.provenance) == 4
