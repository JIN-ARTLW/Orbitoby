import pytest

import orbitoby as ob


class FakeResult:
    def __init__(self):
        self.calls = []

    def compare(self, other):
        self.calls.append(other)
        return {"comparison": "delegated"}


def test_study_compare_delegates_without_recalculation():
    study = ob.study("2024-05-10", "2024-05-11")
    first = FakeResult()
    second = object()

    result = study.compare(first, second)

    assert result == {"comparison": "delegated"}
    assert first.calls == [second]


def test_study_compare_rejects_unimplemented_options():
    study = ob.study("2024-05-10", "2024-05-11")
    first = FakeResult()

    with pytest.raises(TypeError, match="Unsupported"):
        study.compare(first, object(), method="correlation")

    assert first.calls == []


def test_study_compare_requires_comparable_result():
    study = ob.study("2024-05-10", "2024-05-11")

    with pytest.raises(TypeError, match="supporting compare"):
        study.compare(object(), object())
