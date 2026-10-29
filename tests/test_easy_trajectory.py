import pandas as pd
import pytest

from orbitoby._easy_result import DataResult
from orbitoby._easy_trajectory import trajectory_from_density


def example_density():
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2024-05-10T00:00:00Z",
                    "2024-05-10T00:00:30Z",
                ],
                utc=True,
            ),
            "metric": ["thermosphere_neutral_mass_density"] * 2,
            "value": [1e-12, 1.1e-12],
            "unit": ["kg/m3"] * 2,
            "source": ["swarm"] * 2,
            "dataset": ["density_a_pod"] * 2,
            "artifact_id": ["raw-1"] * 2,
            "context": [
                {
                    "Height_GD": 473420.0,
                    "Latitude_GD": 20.0,
                    "Longitude_GD": 125.0,
                },
                {
                    "Height_GD": 473440.0,
                    "Latitude_GD": 21.0,
                    "Longitude_GD": 126.0,
                },
            ],
        }
    )

    return DataResult(
        frame,
        name="Swarm A POD density",
        start="2024-05-10",
        end="2024-05-11",
        source="swarm",
    )


def build(density):
    return trajectory_from_density(
        density,
        satellite="A",
        product="pod",
    )


def test_trajectory_preserves_coordinates_and_lineage():
    result = build(example_density())

    assert len(result.table) == 2
    assert result.table.loc[0, "altitude_km"] == pytest.approx(473.42)
    assert result.table.loc[0, "latitude_deg"] == 20.0

    assert len(result.provenance) == 2
    assert "context" in result.provenance

    assert len(result.parents) == 1
    assert result.parents[0].parent_kind == "raw_artifact"
    assert result.parents[0].parent_id == "raw-1"

    assert "Swarm A" in (result.sources().table.iloc[0]["observed_by"])


def test_missing_coordinates_fail_explicitly():
    density = example_density()
    frame = density.table
    frame.at[0, "context"] = {
        "Latitude_GD": 20.0,
        "Longitude_GD": 125.0,
    }

    broken = DataResult(
        frame,
        name=density.name,
        start=density.start,
        end=density.end,
        source=density.requested_source,
    )

    with pytest.raises(ValueError, match="invalid Height_GD"):
        build(broken)


def test_duplicate_timestamps_fail():
    density = example_density()
    frame = density.table

    frame.loc[1, "timestamp"] = frame.loc[0, "timestamp"]

    broken = DataResult(
        frame,
        name=density.name,
        start=density.start,
        end=density.end,
        source=density.requested_source,
    )

    with pytest.raises(ValueError, match="duplicate timestamps"):
        build(broken)


def test_trajectory_save_has_safe_metadata(tmp_path):
    result = build(example_density())
    path = result.save(tmp_path / "trajectory.csv")

    assert path.exists()
    assert (tmp_path / "trajectory_provenance.csv").exists()
    assert (tmp_path / "trajectory_metadata.json").exists()

    saved = pd.read_csv(path)

    assert "altitude_km" in saved
    assert "context" not in saved

    metadata = (tmp_path / "trajectory_metadata.json").read_text()

    assert "trajectory_input" in metadata
    assert "raw-1" in metadata
