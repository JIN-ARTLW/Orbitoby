from datetime import UTC, datetime
from pathlib import Path

from orbitoby.archive.raw import RawArtifact
from orbitoby.canonical import (
    bindings_for_metric,
    canonicalize_records,
)


def _artifact(
    source,
    dataset,
):
    return RawArtifact(
        artifact_id="artifact-test",
        source=source,
        dataset=dataset,
        norad_id=None,
        requested_start=None,
        requested_end=None,
        retrieved_at=datetime(
            2026,
            10,
            1,
            tzinfo=UTC,
        ),
        sha256="0" * 64,
        path=Path("/tmp/fake"),
    )


def _binding(
    metric,
    source,
    dataset,
):
    matches = [
        binding
        for binding in bindings_for_metric(metric)
        if binding.source == source and binding.dataset == dataset
    ]

    assert len(matches) == 1

    return matches[0]


def test_nrcan_provenance():
    binding = _binding(
        "f107_observed",
        "nrcan",
        "f107_measurements",
    )

    rows = canonicalize_records(
        [
            {
                "time": ("2024-05-10T17:00:00Z"),
                "f107_observed": 214.5,
            }
        ],
        binding,
        artifact=_artifact(
            "nrcan",
            "f107_measurements",
        ),
    )

    row = rows[0]

    assert row["metric"] == ("f107_observed")
    assert row["value"] == 214.5
    assert row["unit"] == "sfu"
    assert row["source"] == "nrcan"
    assert row["artifact_id"] == ("artifact-test")
    assert row["artifact_kind"] == ("measurement")


def test_missing_value_is_preserved():
    binding = _binding(
        "f107_observed",
        "nrcan",
        "f107_measurements",
    )

    rows = canonicalize_records(
        [
            {
                "time": ("2024-05-10T17:00:00Z"),
                "f107_observed": None,
            }
        ],
        binding,
        artifact=None,
    )

    assert rows[0]["value"] is None


def test_swarm_is_provider_derived():
    binding = _binding(
        "thermosphere_neutral_mass_density",
        "swarm",
        "density_a_pod",
    )

    rows = canonicalize_records(
        [
            {
                "Timestamp": ("2015-04-01T00:00:00Z"),
                "density": 8.68e-13,
                "Height_GD": 456615.9,
                "Latitude_GD": 28.3,
                "Longitude_GD": 93.6,
                "local_solar_time": 6.17,
                "validity_flag": 0,
            }
        ],
        binding,
        artifact=None,
    )

    row = rows[0]

    assert row["artifact_kind"] == "provider_derived"

    assert row["unit"] == "kg/m^3"
    assert row["quality_flag"] == 0

    assert row["context"]["Height_GD"] == 456615.9


def test_noaa_speed_unit():
    binding = _binding(
        "solar_wind_speed",
        "noaa",
        "rtsw_wind_1m",
    )

    rows = canonicalize_records(
        [
            {
                "time_tag": ("2026-10-01T00:00:00Z"),
                "proton_speed": 420.0,
            }
        ],
        binding,
        artifact=None,
    )

    assert rows[0]["unit"] == "km/s"


def test_gfz_status_is_canonicalized():
    binding = _binding(
        "kp",
        "gfz",
        "kp",
    )

    rows = canonicalize_records(
        [
            {
                "datetime": ("2024-05-10T00:00:00Z"),
                "Kp": 2.333,
                "status": "def",
            }
        ],
        binding,
        artifact=None,
    )

    row = rows[0]

    assert row["value"] == 2.333
    assert row["status"] == "definitive"
    assert row["provider_status"] == "def"


def test_silso_fill_is_explicit_missing():
    binding = _binding(
        "ssn",
        "silso",
        "sunspot_daily",
    )

    rows = canonicalize_records(
        [
            {
                "year": 2024,
                "month": 5,
                "day": 11,
                "decimal_year": 2024.360,
                "sunspot_number": -1,
                "standard_deviation": -1.0,
                "observations": 0,
                "definitive": 0,
            }
        ],
        binding,
        artifact=None,
    )

    row = rows[0]

    assert row["source_value"] == -1
    assert row["value"] is None
    assert row["is_missing"]
    assert row["missing_reason"] == ("provider_fill")
    assert row["status"] == "provisional"


def test_kyoto_version_and_fill_preserved():
    binding = _binding(
        "dst",
        "wdc_kyoto",
        "dst_hourly",
    )

    rows = canonicalize_records(
        [
            {
                "Time": ("2024-05-10T00:29:30Z"),
                "dstValue": 99999,
                "versionCode": 10,
            }
        ],
        binding,
        artifact=None,
    )

    row = rows[0]

    assert row["source_value"] == 99999
    assert row["value"] is None
    assert row["provider_status"] == 10
    assert row["status"] == "provisional"


def test_cdaweb_fill_is_not_physical_value():
    binding = _binding(
        "solar_wind_speed",
        "cdaweb",
        "omni_hourly",
    )

    rows = canonicalize_records(
        [
            {
                "Time": ("2024-05-10T00:00:00Z"),
                "V1800": 9999.0,
            }
        ],
        binding,
        artifact=None,
    )

    assert rows[0]["source_value"] == 9999.0
    assert rows[0]["value"] is None
    assert rows[0]["is_missing"]


def test_swarm_density_fill_is_explicit_missing():
    from orbitoby.canonical import (
        bindings_for_metric,
        canonicalize_records,
    )

    binding = next(
        binding
        for binding in bindings_for_metric("thermosphere_neutral_mass_density")
        if (binding.source == "swarm" and binding.dataset == "density_a_acc")
    )

    rows = canonicalize_records(
        [
            {
                "Timestamp": "2024-05-10T00:01:50Z",
                "density": 9.99e32,
                "Latitude_GD": 0.0,
                "Longitude_GD": 0.0,
                "Height_GD": 470000.0,
                "local_solar_time": 12.0,
            }
        ],
        binding,
        artifact=None,
    )

    assert len(rows) == 1

    row = rows[0]

    assert row["value"] is None
    assert row["is_missing"] is True
    assert row["missing_reason"] == "provider_fill"
    assert row["source_value"] == 9.99e32
