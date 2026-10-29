import pandas as pd
import pytest

import orbitoby as ob


class FakeArchive:
    def __init__(self):
        self.calls = []

    def orbit(self, **kwargs):
        self.calls.append(kwargs)
        return pd.DataFrame(
            {
                "timestamp": ["2024-05-10T00:00:00Z"],
                "mean_motion": [15.0],
                "source": ["spacetrack"],
            }
        )


def test_single_orbit():
    study = ob.study("2024-05-10", "2024-05-20")
    fake = FakeArchive()
    study._archive = fake

    result = study.orbit(39452)

    assert len(result.table) == 1
    assert result.table.loc[0, "norad_id"] == 39452
    assert fake.calls[0]["source"] == "spacetrack"


def test_multiple_orbits():
    study = ob.study("2024-05-10", "2024-05-20")
    study._archive = FakeArchive()

    result = study.orbit(39452, 39451, sync=False)

    assert len(result.table) == 2
    assert set(result.table["norad_id"]) == {39452, 39451}


def test_invalid_orbit_ids():
    study = ob.study("2024-05-10", "2024-05-20")

    with pytest.raises(ValueError):
        study.orbit()

    with pytest.raises(ValueError):
        study.orbit(-1)

    with pytest.raises(ValueError):
        study.orbit("39452")

    with pytest.raises(ValueError):
        study.orbit(39452, 39452)

    assert study._archive is None
