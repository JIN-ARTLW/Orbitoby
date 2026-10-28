from types import SimpleNamespace

import pandas as pd
import pytest

import orbitoby as ob


class FakeArchive:
    def get_source(self, name):
        assert name == "swarm"
        return SimpleNamespace(
            datasets=(
                "density_a_acc",
                "density_b_acc",
                "density_c_acc",
                "density_a_pod",
                "density_b_pod",
                "density_c_pod",
            )
        )


@pytest.mark.parametrize("letter", ["A", "B", "C"])
def test_swarm_selection_is_lazy(letter):
    study = ob.study("2024-05-10", "2024-05-20")

    swarm = study.swarm(letter.lower())

    assert swarm.satellite == letter
    assert study._archive is None


def test_swarm_products_match_satellite():
    study = ob.study("2024-05-10", "2024-05-20")
    study._archive = FakeArchive()

    swarm = study.swarm("A")

    assert set(swarm.products()) == {
        "density_a_acc",
        "density_a_pod",
    }


def test_invalid_swarm_selection():
    study = ob.study("2024-05-10", "2024-05-20")

    with pytest.raises(ValueError):
        study.swarm("D")

    with pytest.raises(TypeError):
        study.swarm(39452)

    assert study._archive is None


def test_swarm_density_uses_explicit_product():
    import pandas as pd

    class DensityArchive(FakeArchive):
        def __init__(self):
            self.calls = []

        def timeseries(self, metric, **kwargs):
            self.calls.append((metric, kwargs))

            return pd.DataFrame(
                {
                    "timestamp": pd.to_datetime(["2024-05-10T00:00:00Z"], utc=True),
                    "metric": [metric],
                    "value": [1e-12],
                    "unit": ["kg/m3"],
                    "source": ["swarm"],
                    "dataset": [kwargs["dataset"]],
                }
            )

    study = ob.study("2024-05-10", "2024-05-20")
    fake = DensityArchive()
    study._archive = fake

    density = study.swarm("B").density(product="acc")

    assert len(density.table) == 1
    assert fake.calls[0][0] == "thermosphere_neutral_mass_density"
    assert fake.calls[0][1]["dataset"] == "density_b_acc"


def test_invalid_density_product_is_lazy():
    study = ob.study("2024-05-10", "2024-05-20")
    swarm = study.swarm("A")

    with pytest.raises(ValueError):
        swarm.density(product="unknown")

    with pytest.raises(TypeError):
        swarm.density(product=123)

    assert study._archive is None


def test_swarm_altitude_preserves_parent_provenance():
    import pandas as pd

    class AltitudeArchive(FakeArchive):
        def timeseries(self, metric, **kwargs):
            return pd.DataFrame(
                {
                    "timestamp": pd.to_datetime(["2024-05-10T00:00:00Z"], utc=True),
                    "metric": [metric],
                    "value": [1e-12],
                    "unit": ["kg/m3"],
                    "source": ["swarm"],
                    "dataset": [kwargs["dataset"]],
                    "artifact_id": ["raw-swarm-1"],
                    "artifact_kind": ["provider_derived"],
                    "context": [{"Height_GD": 473420.0}],
                }
            )

    study = ob.study("2024-05-10", "2024-05-20")
    study._archive = AltitudeArchive()

    altitude = study.swarm("A").altitude()
    frame = altitude.table

    assert frame.loc[0, "value"] == pytest.approx(473.42)
    assert frame.loc[0, "unit"] == "km"
    assert frame.loc[0, "source_value"] == 473420.0
    assert frame.loc[0, "artifact_id"] == "raw-swarm-1"
    assert frame.loc[0, "dataset"] == "density_a_pod"
    assert frame.loc[0, "artifact_kind"] == "orbitoby_derived"
    assert frame.loc[0, "parent_metric"] == ("thermosphere_neutral_mass_density")


def test_altitude_source_identifies_swarm_platform():
    from orbitoby._easy_sources import source_table

    frame = pd.DataFrame(
        {
            "metric": ["swarm_geodetic_altitude"],
            "source": ["swarm"],
            "dataset": ["density_a_pod"],
        }
    )

    source = source_table(frame).iloc[0]

    assert "Swarm A" in source["observed_by"]
    assert "Orbitoby" in source["produced_by"]
