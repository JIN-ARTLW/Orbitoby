from datetime import date

import pytest

import orbitoby as ob


def test_study_dates():
    study = ob.study("2024-05-10", "2024-05-20")

    assert study.start == date(2024, 5, 10)
    assert study.end == date(2024, 5, 20)
    assert study._archive is None


def test_invalid_period():
    with pytest.raises(ValueError):
        ob.study("2024-05-20", "2024-05-10")

    with pytest.raises(ValueError):
        ob.study("2024-05-10", "2024-05-10")


def test_study_close():
    study = ob.study("2024-05-10", "2024-05-20")
    study.close()

    with pytest.raises(RuntimeError):
        _ = study._core
