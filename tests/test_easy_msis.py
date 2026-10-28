from types import SimpleNamespace

import pandas as pd
import pytest

import orbitoby as ob
from orbitoby import ProductParent


class FakeArchive:
    def __init__(self):
        self.input_calls = []
        self.model_calls = []

    def get_source(self, name):
        assert name == "swarm"
        return SimpleNamespace(datasets=("density_a_pod",))

    def timeseries(self, metric, **kwargs):
        return pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-05-10T00:00:00Z"], utc=True),
                "metric": [metric],
                "value": [1e-12],
                "unit": ["kg/m^3"],
                "source": ["swarm"],
                "dataset": ["density_a_pod"],
                "artifact_id": ["raw-swarm-1"],
                "context": [
                    {
                        "Height_GD": 473420.0,
                        "Latitude_GD": 20.0,
                        "Longitude_GD": 125.0,
                    }
                ],
            }
        )

    def msis_inputs(self, trajectory, *, driver_source, trajectory_parents):
        self.input_calls.append((trajectory.copy(), driver_source))
        lineage = tuple(trajectory_parents) + (
            ProductParent("raw_artifact", "raw-gfz-1", "ap_input"),
        )
        frame = trajectory[
            ["timestamp", "longitude_deg", "latitude_deg", "altitude_km"]
        ].copy()
        frame["f107_previous_day_sfu"] = 200.0
        return frame, lineage

    def msis_density(self, frame, *, parents):
        self.model_calls.append((frame.copy(), tuple(parents)))
        return pd.DataFrame(
            {
                "timestamp": frame["timestamp"],
                "metric": ["thermosphere_neutral_mass_density"],
                "value": [1.2e-12],
                "unit": ["kg/m^3"],
                "source": ["orbitoby"],
                "dataset": ["nrlmsis_2_1_density"],
                "artifact_kind": ["model_output"],
                "model_version": ["2.1"],
                "product_id": ["model-product-1"],
            }
        )


def test_inputs_are_separate_from_model_calculation():
    study = ob.study("2024-05-10", "2024-05-11")
    fake = FakeArchive()
    study._archive = fake

    inputs = study.msis_inputs("A")

    assert len(inputs.table) == 1
    assert len(fake.input_calls) == 1
    assert not fake.model_calls
    assert len(inputs.lineage) == 2
    assert inputs.trajectory.satellite == "A"


def test_model_uses_prepared_inputs_without_refetch():
    study = ob.study("2024-05-10", "2024-05-11")
    fake = FakeArchive()
    study._archive = fake

    inputs = study.msis_inputs("A")
    modeled = study.msis(inputs=inputs)

    assert len(fake.input_calls) == 1
    assert len(fake.model_calls) == 1
    assert len(modeled.table) == 1
    assert modeled.table.loc[0, "artifact_kind"] == "model_output"
    assert modeled.table.loc[0, "model_version"] == "2.1"
    assert len(modeled.lineage) == 2


def test_invalid_driver_rejected_before_download():
    study = ob.study("2024-05-10", "2024-05-11")

    with pytest.raises(ValueError, match="GFZ"):
        study.msis_inputs("A", source="unknown")

    assert study._archive is None


def test_model_lineage_export(tmp_path):
    study = ob.study("2024-05-10", "2024-05-11")
    study._archive = FakeArchive()

    inputs = study.msis_inputs("A")
    modeled = study.msis(inputs=inputs)
    path = modeled.save(tmp_path / "model.csv")

    assert path.exists()
    sidecar = tmp_path / "model_lineage.json"
    assert sidecar.exists()
    assert "raw-gfz-1" in sidecar.read_text()
    assert "2.1" in sidecar.read_text()
