import pandas as pd
import pytest

import orbitoby as ob


class FakeArchive:
    def __init__(self):
        self.orbit_calls = []
        self.screen_calls = []

    def objects(self, **kwargs):
        return pd.DataFrame(
            {
                "norad_id": [39452, 39451, 12345],
                "name": ["Swarm A", "Swarm B", "Example"],
                "catalogue_source": ["celestrak"] * 3,
            }
        )

    def orbit(self, **kwargs):
        self.orbit_calls.append(kwargs)
        return pd.DataFrame(
            {
                "norad_id": [kwargs["norad_id"]],
                "epoch": ["2024-05-10T00:00:00Z"],
                "mean_motion": [15.0],
            }
        )

    def orbit_summary(self, objects, **kwargs):
        self.screen_calls.append((tuple(objects), kwargs))
        return pd.DataFrame(
            {
                "norad_id": list(objects),
                "matches": [value == 39452 for value in objects],
                "observed_day_ratio": [0.9, 0.5],
                "filter_reason": [None, "coverage_below_minimum"],
            }
        )


def test_pick_and_orbit():
    study = ob.study("2024-05-10", "2024-05-20")
    fake = FakeArchive()
    study._archive = fake

    selected = study.satellites(sync=False).pick(39452, 39451)
    orbit = study.orbit(selected, sync=False)

    assert selected.table["norad_id"].tolist() == [39452, 39451]
    assert len(orbit.table) == 2
    assert [x["norad_id"] for x in fake.orbit_calls] == [39452, 39451]


def test_orbit_check():
    study = ob.study("2024-05-10", "2024-05-20")
    fake = FakeArchive()
    study._archive = fake

    result = study.orbit(39452, 39451, sync=False)
    checked = result.check(altitude=(300, 700), coverage=0.8)

    ids, options = fake.screen_calls[0]

    assert ids == (39452, 39451)
    assert options["periapsis_km"] == (300, 700)
    assert options["min_coverage"] == 0.8
    assert options["sync"] is False

    assert len(checked.table) == 2
    assert checked.passed().table["norad_id"].tolist() == [39452]
    assert len(result.table) == 2


def test_invalid_selection_and_altitude():
    study = ob.study("2024-05-10", "2024-05-20")
    study._archive = FakeArchive()

    satellites = study.satellites(sync=False)

    with pytest.raises(ValueError):
        satellites.pick(99999)

    with pytest.raises(ValueError):
        satellites.pick(39452, 39452)

    orbit = study.orbit(39452, sync=False)

    with pytest.raises(ValueError):
        orbit.check(altitude=(300, 700), periapsis=(300, 700))
