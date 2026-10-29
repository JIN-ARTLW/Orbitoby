import pandas as pd
import pytest

import orbitoby as ob


class FakeArchive:
    def __init__(self):
        self.calls = []

    def objects(self, **kwargs):
        self.calls.append(kwargs)
        return pd.DataFrame(
            {
                "norad_id": [39452, 39451],
                "name": ["Swarm A", "Swarm B"],
            }
        )


def test_satellites():
    study = ob.study("2024-05-10", "2024-05-20")
    fake = FakeArchive()
    study._archive = fake

    result = study.satellites(sync=False)

    assert len(result.table) == 2
    assert fake.calls[0]["object_type"] == "payload"
    assert fake.calls[0]["existence"] == "throughout"
    assert fake.calls[0]["sync"] is False
    assert fake.calls[0]["start"] == study.start
    assert fake.calls[0]["end"] == study.end


def test_objects():
    study = ob.study("2024-05-10", "2024-05-20")
    fake = FakeArchive()
    study._archive = fake

    study.objects(type="debris", existence="overlap")

    assert fake.calls[0]["object_type"] == "debris"
    assert fake.calls[0]["existence"] == "overlap"
    assert fake.calls[0]["sync"] is True


def test_invalid_options():
    study = ob.study("2024-05-10", "2024-05-20")

    with pytest.raises(ValueError):
        study.satellites(existence="unknown")

    with pytest.raises(TypeError):
        study.objects(sync="yes")

    assert study._archive is None
