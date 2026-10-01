from __future__ import annotations

from datetime import UTC, datetime

import pytest

from orbitoby.sources.latis import (
    LaTiSClient,
)
from orbitoby.sources.lisird import (
    LISIRDSource,
)


class FakeHTTP:
    def __init__(
        self,
        payload=b"",
    ):
        self.payload = payload
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

        return self.payload


def test_latis_builds_half_open_query():
    fake = FakeHTTP(b"time,value\n2024-05-10T00:00:00Z,1\n")

    client = LaTiSClient(
        base_url=("https://example.test/latis"),
        allowed_hosts=("example.test",),
        http=fake,
    )

    payload = client.fetch_csv(
        "science_data",
        start=datetime(
            2024,
            5,
            10,
            0,
            0,
            tzinfo=UTC,
        ),
        end=datetime(
            2024,
            5,
            11,
            0,
            0,
            tzinfo=UTC,
        ),
        variables=("value",),
        limit=5,
    )

    assert payload.startswith(b"time,value")

    url, kwargs = fake.calls[0]

    assert url == ("https://example.test/latis/dap/science_data.csv")

    query = kwargs["params"]

    assert "time>=2024-05-10T00:00:00Z" in query

    assert "time<2024-05-11T00:00:00Z" in query

    assert "formatTime(yyyy-MM-dd'T'HH:mm:ss'Z')" in query

    assert "project(time,value)" in query
    assert "limit(5)" in query


def test_latis_normalizes_csv():
    payload = b"time,value (W/m^2),count\n2024-05-10T00:00:00Z,1.25,3\n"

    records = LaTiSClient.normalize_csv(payload)

    assert records == [
        {
            "time": ("2024-05-10T00:00:00Z"),
            "value": 1.25,
            "count": 3,
        }
    ]


def test_latis_rejects_unsafe_dataset():
    client = LaTiSClient(
        base_url=("https://example.test/latis"),
        allowed_hosts=("example.test",),
        http=FakeHTTP(),
    )

    with pytest.raises(ValueError):
        client.fetch_csv(
            "../secret",
            start="2024-01-01",
            end="2024-01-02",
        )


def test_lisird_exposes_fism2():
    source = LISIRDSource()

    assert source.LATIS_PROFILES["fism2_daily_bands"] == "fism_daily_bands"

    assert source.LATIS_PROFILES["fism2_daily_spectrum"] == "fism_daily_hr"

    assert source.LATIS_PROFILES["fism2_flare_bands"] == "fism_flare_bands"

    assert source.LATIS_PROFILES["fism2_flare_spectrum"] == "fism_flare_hr"

    assert source.raw_extension == "csv"


def test_lisird_data_uses_latis():
    source = LISIRDSource()

    fake = FakeHTTP(b"time,value\n2024-05-10T00:00:00Z,1\n")

    source.latis.http = fake

    payload = source.fetch(
        "eve_bands",
        start="2024-05-10",
        end="2024-05-11",
        limit=1,
    )

    assert payload.startswith(b"time,value")

    url, _ = fake.calls[0]

    assert url.endswith("/dap/sdo_eve_bands_l3.csv")


def test_lisird_fism2_uses_native_id():
    source = LISIRDSource()

    fake = FakeHTTP(b"time,ssi\n2024-05-10T12:00:00Z,1\n")

    source.latis.http = fake

    source.fetch(
        "fism2_daily_bands",
        start="2024-05-10",
        end="2024-05-11",
    )

    url, _ = fake.calls[0]

    assert url.endswith("/dap/fism_daily_bands.csv")


def test_lisird_raw_latis_dataset_ids_are_allowed():
    source = LISIRDSource()

    fake = FakeHTTP(b"time,value\n2024-05-10T00:00:00Z,1\n")

    source.latis.http = fake

    payload = source.fetch(
        "some_future_dataset",
        start="2024-05-10",
        end="2024-05-11",
        limit=1,
    )

    assert payload.startswith(b"time,value")

    url, _ = fake.calls[0]

    assert url.endswith("/dap/some_future_dataset.csv")


def test_lisird_latis_shares_initial_http_client():
    source = LISIRDSource()

    assert source.latis.http is source.http
