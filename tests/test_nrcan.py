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
