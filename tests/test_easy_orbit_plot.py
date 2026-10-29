import pandas as pd
import pytest

import orbitoby as ob


class FakeArchive:
    def orbit(self, **kwargs):
        norad_id = kwargs["norad_id"]

        return pd.DataFrame(
            {
                "epoch": pd.to_datetime(
                    [
                        "2024-05-10T00:00:00Z",
                        "2024-05-10T03:00:00Z",
                    ],
                    utc=True,
                ),
                "norad_id": [norad_id, norad_id],
                "periapsis_km": [450.0, 449.5],
                "apoapsis_km": [465.0, 464.5],
                "inclination_deg": [87.2, 87.3],
                "mean_motion": [15.1, 15.2],
                "eccentricity": [0.001, 0.0011],
                "source": ["spacetrack"] * 2,
                "dataset": ["gp_history"] * 2,
                "artifact_id": [f"raw-{norad_id}"] * 2,
            }
        )


def study_with_archive():
    study = ob.study("2024-05-10", "2024-05-11")
    study._archive = FakeArchive()
    return study


def test_default_orbit_plot_is_periapsis_scatter():
    study = study_with_archive()
    orbit = study.orbit(39452)

    figure = orbit.plot()

    assert "periapsis_km" in figure.svg
    assert "NORAD 39452" in figure.svg
    assert "<circle" in figure.svg
    assert len(figure.provenance) == 2


def test_orbit_plot_separates_satellites():
    study = study_with_archive()
    orbit = study.orbit(39452, 39451)

    figure = orbit.plot("inclination")

    assert "NORAD 39452" in figure.svg
    assert "NORAD 39451" in figure.svg
    assert "inclination_deg" in figure.svg
    assert len(figure.provenance) == 4
    assert set(figure.provenance["norad_id"]) == {39452, 39451}


def test_orbit_plot_preserves_original_epochs():
    study = study_with_archive()
    orbit = study.orbit(39452)
    figure = orbit.plot("mean motion")

    original_times = pd.to_datetime(orbit.table["epoch"], utc=True)
    plotted_times = pd.to_datetime(figure.provenance["timestamp"], utc=True)

    assert original_times.tolist() == plotted_times.tolist()
    assert figure.provenance["unit"].eq("rev/day").all()


def test_unavailable_element_fails_explicitly():
    study = study_with_archive()
    orbit = study.orbit(39452)

    # Supported element, but absent from this provider result.
    orbit._frame = orbit.table.drop(columns=["apoapsis_km"])

    with pytest.raises(ValueError, match="unavailable"):
        orbit.plot("apoapsis")


def test_invalid_element_name_fails_explicitly():
    study = study_with_archive()
    orbit = study.orbit(39452)

    with pytest.raises(ValueError, match="Unknown orbital element"):
        orbit.plot("made up variable")


def test_duplicate_epoch_is_rejected():
    study = study_with_archive()
    orbit = study.orbit(39452)

    frame = orbit._frame.copy()
    frame.loc[1, "epoch"] = frame.loc[0, "epoch"]
    orbit._frame = frame

    with pytest.raises(ValueError, match="Multiple orbital records"):
        orbit.plot()
