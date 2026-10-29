import pandas as pd
import pytest

from orbitoby._easy_result import DataResult


def make_result(values, timestamps, *, source, role, unit="kg/m^3"):
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(timestamps, utc=True),
            "metric": ["thermosphere_neutral_mass_density"] * len(values),
            "value": values,
            "unit": [unit] * len(values),
            "source": [source] * len(values),
            "dataset": [source + "_density"] * len(values),
            "artifact_kind": [role] * len(values),
            "context": ["PRIVATE_CONTEXT"] * len(values),
        }
    )
    return DataResult(
        frame,
        name=source + " density",
        start="2024-05-10",
        end="2024-05-11",
        source=source,
    )


def examples():
    left = make_result(
        [1.0e-12, 2.0e-12],
        ["2024-05-10T00:00:00Z", "2024-05-10T00:00:30Z"],
        source="swarm",
        role="provider_derived",
    )
    right = make_result(
        [1.1e-12, 2.1e-12],
        ["2024-05-10T00:00:00Z", "2024-05-10T00:01:00Z"],
        source="orbitoby",
        role="model_output",
    )
    return left, right


def test_comparison_preserves_exact_union():
    left, right = examples()
    result = left.compare(right)

    assert len(result.aligned) == 3
    assert result.aligned["exact_record_match"].sum() == 1
    assert result.aligned["comparable_values"].sum() == 1
    assert len(result.provenance) == 4


def test_comparison_plot_has_two_distinct_series():
    left, right = examples()
    figure = left.compare(right).plot()

    assert "swarm" in figure.svg
    assert "orbitoby" in figure.svg
    assert len(figure.provenance) == 4


def test_comparison_rejects_incompatible_units():
    left, right = examples()
    frame = right.table
    frame["unit"] = "g/cm^3"

    other = DataResult(
        frame,
        name=right.name,
        start=right.start,
        end=right.end,
        source=right.requested_source,
    )
    with pytest.raises(ValueError, match="Incompatible units"):
        left.compare(other)


def test_comparison_does_not_export_private_context(tmp_path):
    left, right = examples()
    result = left.compare(right)

    path = result.save(tmp_path / "compare.csv")

    assert path.exists()
    assert (tmp_path / "compare_provenance.csv").exists()
    assert (tmp_path / "compare_sources.csv").exists()
    assert (tmp_path / "compare_metadata.json").exists()

    assert "PRIVATE_CONTEXT" not in (tmp_path / "compare_provenance.csv").read_text()
    assert "PRIVATE_CONTEXT" not in result.plot().svg


def test_duplicate_timestamps_are_rejected():
    left, right = examples()
    frame = right.table
    frame.loc[1, "timestamp"] = frame.loc[0, "timestamp"]

    other = DataResult(
        frame,
        name=right.name,
        start=right.start,
        end=right.end,
        source=right.requested_source,
    )
    with pytest.raises(ValueError, match="duplicate timestamps"):
        left.compare(other)
