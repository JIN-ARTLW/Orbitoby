from __future__ import annotations

import json

import pytest

from orbitoby.auth import CredentialManager
from orbitoby.http import SafeHttpClient
from orbitoby.sources.donki import (
    DONKISource,
)
from orbitoby.sources.noaa import (
    NoaaSource,
)
from orbitoby.sources.registry import (
    build_sources,
)


class FakeHTTP:
    def __init__(
        self,
        payload: bytes = b"[]",
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


def test_noaa_expanded_products_use_safe_http():
    source = NoaaSource()

    assert isinstance(
        source.http,
        SafeHttpClient,
    )

    assert "goes_xray_1day" in source.datasets

    assert "rtsw_mag_1m" in source.datasets

    assert source.URLS["goes_xray_1day"].endswith("/json/goes/primary/xrays-1-day.json")


def test_noaa_rejects_range_params():
    source = NoaaSource(http=FakeHTTP())

    with pytest.raises(ValueError):
        source.fetch(
            "goes_xray_1day",
            start="2024-05-10",
        )


def test_noaa_table_json_is_strict():
    source = NoaaSource(http=FakeHTTP())

    payload = json.dumps(
        [
            [
                "time_tag",
                "value",
            ],
            [
                "2024-05-10T00:00:00Z",
                1.0,
            ],
        ]
    ).encode()

    assert source.normalize(
        "dst_recent",
        payload,
    ) == [
        {
            "time_tag": ("2024-05-10T00:00:00Z"),
            "value": 1.0,
        }
    ]


def test_donki_uses_safe_http():
    source = DONKISource(credentials=CredentialManager())

    assert isinstance(
        source.http,
        SafeHttpClient,
    )

    assert source.http.allowed_hosts == {"ccmc.gsfc.nasa.gov"}


def test_donki_half_open_day_range():
    fake = FakeHTTP()

    source = DONKISource(
        credentials=CredentialManager(),
        http=fake,
    )

    source.fetch(
        "geomagnetic_storm",
        start="2024-05-10",
        end="2024-05-12",
    )

    _, kwargs = fake.calls[0]

    assert kwargs["params"]["startDate"] == "2024-05-10"

    # NASA endDate is inclusive.
    assert kwargs["params"]["endDate"] == "2024-05-11"


def test_donki_rejects_subday_boundaries():
    source = DONKISource(
        credentials=CredentialManager(),
        http=FakeHTTP(),
    )

    with pytest.raises(ValueError):
        source.fetch(
            "cme",
            start=("2024-05-10T12:00:00Z"),
            end="2024-05-11",
        )


def test_donki_cme_analysis_params():
    fake = FakeHTTP()

    source = DONKISource(
        credentials=CredentialManager(),
        http=fake,
    )

    source.fetch(
        "cme_analysis",
        start="2024-05-10",
        end="2024-05-11",
        most_accurate_only=True,
        complete_entry_only=False,
        speed=500,
        half_angle=30,
        catalog="ALL",
    )

    _, kwargs = fake.calls[0]
    params = kwargs["params"]

    assert params["mostAccurateOnly"] == "true"

    assert params["completeEntryOnly"] == "false"

    assert params["speed"] == 500
    assert params["halfAngle"] == 30


def test_donki_notifications_range_limit():
    source = DONKISource(
        credentials=CredentialManager(),
        http=FakeHTTP(),
    )

    with pytest.raises(ValueError):
        source.fetch(
            "notifications",
            start="2024-01-01",
            end="2024-02-15",
        )


def test_donki_normalizes_event_list():
    source = DONKISource(
        credentials=CredentialManager(),
        http=FakeHTTP(),
    )

    payload = json.dumps(
        [
            {
                "flrID": "example",
                "beginTime": ("2024-05-10T00:00Z"),
            }
        ]
    ).encode()

    records = source.normalize(
        "solar_flare",
        payload,
    )

    assert records[0]["flrID"] == "example"


def test_donki_skips_identity_store():
    source = DONKISource(credentials=CredentialManager())

    assert not source.should_index_identity("cme")


def test_donki_uses_official_ccmc_endpoint():
    fake = FakeHTTP()

    source = DONKISource(
        http=fake,
    )

    source.fetch(
        "solar_flare",
        start="2024-05-10",
        end="2024-05-11",
    )

    url, kwargs = fake.calls[0]

    assert url == ("https://ccmc.gsfc.nasa.gov/DONKI-API/get/FLR")

    assert "api_key" not in kwargs["params"]


def test_donki_api_profile_matches_source_policy():
    source = DONKISource(
        http=FakeHTTP(),
    )

    assert source.api_profile.revision == "2026-09-30"
    assert source.api_profile.base_url == ("https://ccmc.gsfc.nasa.gov/DONKI-API/get")
    assert "ccmc.gsfc.nasa.gov" in source.metadata.host_allowlist


def test_donki_requires_no_credentials(
    tmp_path,
):
    sources = build_sources(settings_path=(tmp_path / "settings.json"))

    assert isinstance(
        sources["donki"],
        DONKISource,
    )
