import pandas as pd
import pytest

import orbitoby as ob


class FakeArchive:
    def __init__(self):
        self.calls = []

    def space_weather(self, **kwargs):
        self.calls.append(kwargs)
        return pd.DataFrame(
            {
                "timestamp": ["2024-05-10T00:00:00Z"],
                "metric": ["kp"],
                "value": [3.0],
                "source": ["gfz"],
            }
        )


def test_weather_calls_core():
    study = ob.study("2024-05-10", "2024-05-20")
    fake = FakeArchive()
    study._archive = fake

    kp = study.weather("Kp")

    assert fake.calls == [
        {
            "start": study.start,
            "end": study.end,
            "fields": "kp",
            "source": "gfz",
        }
    ]
    assert kp.table.iloc[0]["value"] == 3.0


def test_weather_alias():
    study = ob.study("2024-05-10", "2024-05-20")
    fake = FakeArchive()
    study._archive = fake

    study.weather("F10.7")
    assert fake.calls[0]["fields"] == "f107_observed"


def test_unknown_weather_is_safe():
    study = ob.study("2024-05-10", "2024-05-20")

    with pytest.raises(ValueError, match="Unknown weather"):
        study.weather("unknown")

    assert study._archive is None


def test_result_save(tmp_path):
    study = ob.study("2024-05-10", "2024-05-20")
    study._archive = FakeArchive()

    kp = study.weather("Kp")
    path = kp.save(tmp_path / "kp.csv")

    saved = pd.read_csv(path)
    assert len(saved) == 1
    assert saved.loc[0, "source"] == "gfz"
