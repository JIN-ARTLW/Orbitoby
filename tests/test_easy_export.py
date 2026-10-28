import pandas as pd
import pytest

from orbitoby._easy_result import DataResult


def result(frame):
    return DataResult(
        frame,
        name="Scientific data",
        start="2024-05-10",
        end="2024-05-11",
        source="test_provider",
    )


def test_export_preserves_science_but_excludes_context(tmp_path):
    data = result(
        pd.DataFrame(
            {
                "timestamp": ["2024-05-10T00:00:00Z"],
                "metric": ["density"],
                "value": [1.25e-12],
                "unit": ["kg/m^3"],
                "source": ["test_provider"],
                "dataset": ["density_product"],
                "artifact_id": ["raw-artifact-1"],
                "context": [{"access_token": "PRIVATE_SECRET"}],
                "api_key": ["PRIVATE_SECRET"],
            }
        )
    )

    path = data.save(tmp_path / "research.csv")
    exported = pd.read_csv(path)

    assert exported.loc[0, "value"] == pytest.approx(1.25e-12)
    assert exported.loc[0, "artifact_id"] == "raw-artifact-1"
    assert "context" not in exported
    assert "api_key" not in exported

    assert "PRIVATE_SECRET" not in path.read_text()
    assert (tmp_path / "research_export.json").exists()

    # The original result must remain intact.
    assert "context" in data.table
    assert "api_key" in data.table


def test_export_rejects_unreviewed_urls(tmp_path):
    data = result(
        pd.DataFrame(
            {
                "timestamp": ["2024-05-10T00:00:00Z"],
                "value": [1.0],
                "source_value": ["https://example.org/private?token=SECRET"],
            }
        )
    )

    path = tmp_path / "unsafe.csv"

    with pytest.raises(ValueError, match="private"):
        data.save(path)

    assert not path.exists()
