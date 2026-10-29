import json
from xml.etree import ElementTree as ET

import pandas as pd

from orbitoby._easy_result import DataResult, SourceList


class ModelWithInputs(DataResult):
    def source_dependencies(self):
        return pd.DataFrame(
            [
                {
                    "metric": "solar index",
                    "source": "provider_one",
                    "dataset": "solar_data",
                },
                {
                    "metric": "trajectory",
                    "source": "provider_two",
                    "dataset": "orbit_data",
                },
            ]
        )

    def sources(self):
        records = pd.concat(
            [self.table, self.source_dependencies()],
            ignore_index=True,
        )
        return SourceList(records, self.requested_source)


def test_model_input_sources_link_to_plotted_output():
    model = ModelWithInputs(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-05-10T00:00:00Z"], utc=True),
                "metric": ["density"],
                "value": [1e-12],
                "unit": ["kg/m^3"],
                "source": ["model_provider"],
                "dataset": ["density_model"],
                "artifact_kind": ["model_output"],
            }
        ),
        name="Test model density",
        start="2024-05-10",
        end="2024-05-11",
        source="model_provider",
    )

    figure = model.plot()
    root = ET.fromstring(figure.svg)

    ns = "{http://www.w3.org/2000/svg}"
    metadata = json.loads(root.find(f"{ns}metadata").text)

    sources = metadata["sources"]
    usage = metadata["source_usage"]

    assert len(sources) == 3
    assert len(usage) == 1

    refs = {(row["source"], row["dataset"]): row["source_ref"] for row in sources}

    model_ref = refs[("model_provider", "density_model")]

    assert usage[0]["output_ref"] == model_ref

    input_refs = {entry["source_ref"] for entry in usage[0]["inputs"]}

    assert input_refs == {
        refs[("provider_one", "solar_data")],
        refs[("provider_two", "orbit_data")],
    }

    assert "solar index" in figure.svg
    assert "trajectory" in figure.svg
    assert "inputs:" in figure.svg
    assert len(figure.provenance) == 1
