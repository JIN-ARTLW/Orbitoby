from __future__ import annotations

import json
from datetime import date

import pytest

from orbitoby.http import (
    SafeHttpClient,
)
from orbitoby.sources.cdaweb import (
    CDAWebSource,
)
from orbitoby.sources.lisird import (
    LISIRDSource,
)
from orbitoby.sources.registry import (
    build_sources,
)
from orbitoby.sources.wdc_kyoto import (
    WDCKyotoSource,
)


class FakeHTTP:
    def __init__(
        self,
        payload: bytes,
    ) -> None:
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


def hapi_payload(
    *,
    code=1200,
    parameters=None,
    data=None,
):
    return json.dumps(
        {
            "HAPI": "3.3",
            "status": {
                "code": code,
                "message": ("OK" if code == 1200 else ("OK - no data for time range")),
            },
            "parameters": (parameters if parameters is not None else []),
            "data": (data if data is not None else []),
        }
    ).encode("utf-8")


@pytest.mark.parametrize(
    "source_class",
    [
        CDAWebSource,
        LISIRDSource,
        WDCKyotoSource,
    ],
)
def test_hapi_sources_use_safe_http(
    source_class,
):
    source = source_class()

    assert isinstance(
        source.http,
        SafeHttpClient,
    )

    assert source.http.allowed_hosts == set(source.metadata.host_allowlist)


def test_cdaweb_uses_hapi2_request_names():
    source = CDAWebSource()

    fake = FakeHTTP(hapi_payload())

    source.http = fake

    source.fetch(
        "omni_hourly",
        start=date(
            2024,
            5,
            10,
        ),
        end=date(
            2024,
            5,
            11,
        ),
        parameters=[
            "BX_GSE",
            "BY_GSE",
        ],
    )

    url, kwargs = fake.calls[0]

    assert url.endswith("/data")

    assert kwargs["params"] == {
        "format": "json",
        "id": ("OMNI2_H0_MRG1HR"),
        "time.min": ("2024-05-10T00:00:00Z"),
        "time.max": ("2024-05-11T00:00:00Z"),
        "parameters": ("BX_GSE,BY_GSE"),
    }


def test_hapi3_uses_dataset_start_stop():
    source = WDCKyotoSource()

    fake = FakeHTTP(hapi_payload())

    source.http = fake

    source.fetch(
        "dst_hourly",
        start="2024-05-10",
        end="2024-05-12",
    )

    _, kwargs = fake.calls[0]

    assert kwargs["params"] == {
        "format": "json",
        "dataset": "hour_dst",
        "start": ("2024-05-10T00:00:00Z"),
        "stop": ("2024-05-12T00:00:00Z"),
    }


def test_raw_hapi_dataset_ids_are_allowed():
    source = WDCKyotoSource()

    fake = FakeHTTP(hapi_payload())

    source.http = fake

    source.fetch(
        "some_future_dataset",
        start="2024-01-01",
        end="2024-01-02",
    )

    _, kwargs = fake.calls[0]

    assert kwargs["params"]["dataset"] == "some_future_dataset"


def test_hapi_normalization_preserves_fields():
    source = WDCKyotoSource()

    payload = hapi_payload(
        parameters=[
            {
                "name": "Time",
                "type": "isotime",
            },
            {
                "name": "dstValue",
                "type": "integer",
                "fill": "99999",
            },
            {
                "name": "versionCode",
                "type": "integer",
            },
        ],
        data=[
            [
                ("2024-05-10T00:29:30Z"),
                -12,
                2,
            ],
            [
                ("2024-05-10T01:29:30Z"),
                -15,
                2,
            ],
        ],
    )

    records = source.normalize(
        "dst_hourly",
        payload,
    )

    assert records == [
        {
            "Time": ("2024-05-10T00:29:30Z"),
            "dstValue": -12,
            "versionCode": 2,
        },
        {
            "Time": ("2024-05-10T01:29:30Z"),
            "dstValue": -15,
            "versionCode": 2,
        },
    ]


def test_hapi_does_not_silently_replace_fill():
    source = WDCKyotoSource()

    payload = hapi_payload(
        parameters=[
            {
                "name": "Time",
                "type": "isotime",
            },
            {
                "name": "dstValue",
                "type": "integer",
                "fill": "99999",
            },
        ],
        data=[
            [
                ("2024-05-10T00:29:30Z"),
                99999,
            ]
        ],
    )

    records = source.normalize(
        "dst_hourly",
        payload,
    )

    assert records[0]["dstValue"] == 99999


def test_hapi_1201_returns_empty_records():
    source = LISIRDSource()

    payload = hapi_payload(
        code=1201,
    )

    assert (
        source.normalize(
            "solar_radio",
            payload,
        )
        == []
    )


def test_hapi_rejects_non_half_open_range():
    source = CDAWebSource()

    with pytest.raises(
        ValueError,
        match="start must be before end",
    ):
        source.fetch(
            "omni_hourly",
            start="2024-05-10",
            end="2024-05-10",
        )


def test_hapi_catalog():
    source = LISIRDSource()

    payload = json.dumps(
        {
            "HAPI": "3.0",
            "status": {
                "code": 1200,
                "message": "OK",
            },
            "catalog": [
                {
                    "id": ("sdo_eve_bands_l3"),
                    "title": "EVE",
                }
            ],
        }
    ).encode("utf-8")

    source.http = FakeHTTP(payload)

    catalog = source.catalog()

    assert catalog[0]["id"] == "sdo_eve_bands_l3"


def test_hapi_info_resolves_curated_alias():
    source = WDCKyotoSource()

    payload = json.dumps(
        {
            "HAPI": "3.3",
            "status": {
                "code": 1200,
                "message": "OK",
            },
            "parameters": [],
            "startDate": ("1957-01-01T00:00:00Z"),
            "stopDate": ("2026-01-01T00:00:00Z"),
        }
    ).encode("utf-8")

    fake = FakeHTTP(payload)

    source.http = fake

    source.info("dst_hourly")

    _, kwargs = fake.calls[0]

    assert kwargs["params"] == {"dataset": "hour_dst"}


def test_registry_contains_science_hapi_sources(
    tmp_path,
):
    sources = build_sources(settings_path=(tmp_path / "settings.json"))

    assert "cdaweb" in sources
    assert "lisird" in sources
    assert "wdc_kyoto" in sources
