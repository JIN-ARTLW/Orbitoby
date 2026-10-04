from orbitoby.http import SafeHttpClient
from orbitoby.sources.nrcan import NRCanSource

SAMPLE = b"""\
fluxdate    fluxtime    fluxjulian    fluxcarrington  fluxobsflux  fluxadjflux  fluxursi
----------  ----------  ------------  --------------  -----------  -----------  ----------
20240510    170000      02460441.208  002285.000      000214.5     000218.8     000196.9
20240510    200000      02460441.333  002285.000      000223.4     000227.9     000205.1
20240510    230000      02460441.458  002285.000      000230.8     000235.4     000211.9
20240511    170000      02460442.208  002285.000      000255.0     000260.2     000234.2
"""


class FakeHTTP:
    def __init__(self):
        self.calls = []

    def get(
        self,
        url,
        **kwargs,
    ):
        self.calls.append(
            (
                url,
                kwargs,
            )
        )

        return SAMPLE


def test_nrcan_uses_safe_http():
    source = NRCanSource()

    assert isinstance(
        source.http,
        SafeHttpClient,
    )


def test_nrcan_preserves_three_flux_series():
    source = NRCanSource()

    records = source.normalize(
        "f107_measurements",
        SAMPLE,
        start="2024-05-10",
        end="2024-05-11",
    )

    assert len(records) == 3

    first = records[0]

    assert first["time"] == ("2024-05-10T17:00:00Z")

    assert first["f107_observed"] == 214.5

    assert first["f107_adjusted"] == 218.8

    assert first["f107_series_d"] == 196.9

    assert first["unit"] == "sfu"


def test_nrcan_half_open_interval():
    source = NRCanSource()

    records = source.normalize(
        "f107_measurements",
        SAMPLE,
        start="2024-05-10T20:00:00Z",
        end="2024-05-11T17:00:00Z",
    )

    assert [record["time"] for record in records] == [
        "2024-05-10T20:00:00Z",
        "2024-05-10T23:00:00Z",
    ]


def test_nrcan_fetch_uses_official_archive():
    source = NRCanSource()

    fake = FakeHTTP()
    source.http = fake

    payload = source.fetch(
        "f107_measurements",
        start="2024-05-10",
        end="2024-05-11",
    )

    assert payload == SAMPLE

    url, _ = fake.calls[0]

    assert url.endswith("/solar_flux_data/daily_flux_values/fluxtable.txt")


def test_nrcan_skips_identity_store():
    source = NRCanSource()

    assert not source.should_index_identity("f107_measurements")


LEGACY_DAILY_SAMPLE = b"""\
"------------------------------------------------------------------------"
"Julian Date,  Rotation,  year,  mo,  dy,   Obs.,   Adj.,    URSI-D"
"------------------------------------------------------------------------"
2432187.20,  1248.2754,  1947,  01,  01,     .0,     .0,     .0
2432231.20,  1249.8847,  1947,  02,  14,  260.4,  254.0,  228.6
"""


LEGACY_MEASUREMENT_SAMPLE = b"""\
Julian Day   Carrington  <---Date--->   U.T. Flux Density Values in s.f.u.
Number        Rotation   Year  Mo  Dy        Observed  Adjusted  Series D
=========================================================================
02450128.250  01906.052  1996  02  14  1800  000068.6  000066.9  000060.2
02454132.333  002052.856  2007  01  31  2000  000089.2  000086.6  000077.9  1  0  SEC
"""


def test_nrcan_exposes_historical_artifacts():
    source = NRCanSource()

    assert "f107_legacy_daily_1947_1996" in source.datasets

    assert "f107_legacy_measurements_1996_2007" in source.datasets


def test_nrcan_legacy_daily_parser():
    source = NRCanSource()

    records = source.normalize(
        "f107_legacy_daily_1947_1996",
        LEGACY_DAILY_SAMPLE,
    )

    assert len(records) == 2

    assert records[0]["time"] == ("1947-01-01T16:48:00Z")

    # Provider value is preserved exactly.
    # Orbitoby does not silently reinterpret
    # historical zero values as missing.
    assert records[0]["f107_observed"] == 0.0

    assert records[1]["f107_observed"] == 260.4
    assert records[1]["f107_adjusted"] == 254.0
    assert records[1]["f107_series_d"] == 228.6


def test_nrcan_legacy_measurement_parser():
    source = NRCanSource()

    records = source.normalize(
        "f107_legacy_measurements_1996_2007",
        LEGACY_MEASUREMENT_SAMPLE,
    )

    assert len(records) == 2

    assert records[0]["time"] == ("1996-02-14T18:00:00Z")

    assert records[0]["f107_observed"] == 68.6
    assert records[0]["f107_adjusted"] == 66.9
    assert records[0]["f107_series_d"] == 60.2


def test_nrcan_preserves_unknown_legacy_extra_fields():
    source = NRCanSource()

    records = source.normalize(
        "f107_legacy_measurements_1996_2007",
        LEGACY_MEASUREMENT_SAMPLE,
    )

    assert records[1]["provider_extra_fields"] == [
        "1",
        "0",
        "SEC",
    ]


def test_nrcan_historical_fetch_urls():
    fake = FakeHTTP()

    source = NRCanSource(
        http=fake,
    )

    source.fetch("f107_legacy_daily_1947_1996")

    source.fetch("f107_legacy_measurements_1996_2007")

    assert fake.calls[0][0].endswith("/F107_1947_1996.txt")

    assert fake.calls[1][0].endswith("/F107_1996_2007.txt")


def test_nrcan_legacy_daily_recovers_missing_comma():
    source = NRCanSource()

    payload = b"""\
2450044.33,  1902.9795,  1995,  11,  22,   72.8,   71.0    63.9
"""

    records = source.normalize(
        "f107_legacy_daily_1947_1996",
        payload,
    )

    assert len(records) == 1

    record = records[0]

    assert record["f107_observed"] == 72.8
    assert record["f107_adjusted"] == 71.0
    assert record["f107_series_d"] == 63.9

    assert record["provider_parse_recovery"] == ("missing_comma_recovered")


def test_nrcan_legacy_measurement_preserves_missing_flux():
    source = NRCanSource()

    payload = b"""\
02450579.333  01922.591  1997  05  10  2000
02450579.458  01922.595  1997  05  10  2300  000073.3  000074.8  000067.3
"""

    records = source.normalize(
        "f107_legacy_measurements_1996_2007",
        payload,
    )

    assert len(records) == 2

    missing = records[0]

    assert missing["time"] == ("1997-05-10T20:00:00Z")
    assert missing["f107_observed"] is None
    assert missing["f107_adjusted"] is None
    assert missing["f107_series_d"] is None
    assert missing["unit"] == "sfu"

    assert missing["provider_record_status"] == ("missing_flux_values")

    assert records[1]["f107_observed"] == 73.3
