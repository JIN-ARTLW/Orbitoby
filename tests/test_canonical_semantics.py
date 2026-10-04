from dataclasses import fields

from orbitoby.canonical import (
    METRIC_BINDINGS,
    CanonicalObservation,
)


def _bindings(source, dataset):
    return [
        binding
        for binding in METRIC_BINDINGS
        if binding.source == source and binding.dataset == dataset
    ]


def test_canonical_observation_records_method():
    names = {field.name for field in fields(CanonicalObservation)}

    assert "method" in names


def test_nrcan_measurement_intervals_are_instants():
    for dataset in (
        "f107_measurements",
        "f107_legacy_measurements_1996_2007",
    ):
        bindings = _bindings(
            "nrcan",
            dataset,
        )

        assert bindings
        assert {binding.interval_kind for binding in bindings} == {"instant"}


def test_nrcan_legacy_daily_is_daily():
    bindings = _bindings(
        "nrcan",
        "f107_legacy_daily_1947_1996",
    )

    assert bindings
    assert {binding.interval_kind for binding in bindings} == {"day"}


def test_swarm_acc_method_is_explicit():
    for dataset in (
        "density_a_acc",
        "density_b_acc",
        "density_c_acc",
    ):
        bindings = _bindings(
            "swarm",
            dataset,
        )

        assert bindings
        assert {binding.artifact_kind for binding in bindings} == {"provider_derived"}

        assert {binding.method for binding in bindings} == {"accelerometer_retrieval"}


def test_swarm_pod_method_is_explicit():
    for dataset in (
        "density_a_pod",
        "density_b_pod",
        "density_c_pod",
    ):
        bindings = _bindings(
            "swarm",
            dataset,
        )

        assert bindings
        assert {binding.artifact_kind for binding in bindings} == {"provider_derived"}

        assert {binding.method for binding in bindings} == {"pod_retrieval"}
