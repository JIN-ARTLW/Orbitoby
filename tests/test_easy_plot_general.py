import pandas as pd

from orbitoby._easy_result import DataResult

TIMES = pd.to_datetime(
    ["2024-05-10T00:00:00Z", "2024-05-10T00:00:30Z"],
    utc=True,
)


def result(metric, values, unit, *, role="observation", source="test"):
    frame = pd.DataFrame(
        {
            "timestamp": TIMES,
            "metric": [metric] * 2,
            "value": values,
            "unit": [unit] * 2,
            "source": [source] * 2,
            "dataset": ["shared_dataset"] * 2,
            "artifact_kind": [role] * 2,
        }
    )

    return DataResult(
        frame,
        name=f"{metric}: {role}",
        start="2024-05-10",
        end="2024-05-11",
        source=source,
    )


def test_different_physical_quantities_use_separate_panels():
    density = result("density", [1e-12, 2e-12], "kg/m^3")
    velocity = result("velocity", [7000, 7500], "m/s")
    temperature = result("temperature", [500, 600], "K")

    figure = density.plot(below=[velocity, temperature])

    for name in ("density", "velocity", "temperature"):
        assert f"<title>{name}</title>" in figure.svg

    assert len(figure.provenance) == 6


def test_scientific_axis_scales_both_small_and_large_values():
    density = result("density", [1e-12, 2e-12], "kg/m^3")
    acceleration = result("acceleration", [1e7, 2e7], "m/s^2")

    svg = density.plot(below=acceleration).svg

    assert "× 10⁻¹²" in svg
    assert "× 10⁷" in svg


def test_negative_scientific_values():
    field = result("electric_field", [-2e-8, -1e-8], "V/m")
    svg = field.plot().svg

    assert "× 10⁻⁸" in svg


def test_two_model_results_are_not_labeled_observed():
    a = result(
        "density",
        [1e-12, 2e-12],
        "kg/m^3",
        role="model_output",
    )
    b = result(
        "density",
        [1.5e-12, 2.5e-12],
        "kg/m^3",
        role="model_output",
    )

    comparison = a.compare(b)
    svg = comparison.plot().svg

    assert "density: model_output [test / shared_dataset] (Left)" in svg
    assert "density: model_output [test / shared_dataset] (Right)" in svg
    assert len(comparison.provenance) == 4


def test_comparing_two_observations_preserves_roles():
    a = result("speed", [10, 20], "m/s", role="observation")
    b = result("speed", [11, 21], "m/s", role="observation")

    svg = a.compare(b).plot().svg

    assert "speed: observation [test / shared_dataset] (Left)" in svg
    assert "speed: observation [test / shared_dataset] (Right)" in svg
    assert "speed: model_output [test / shared_dataset]" not in svg
