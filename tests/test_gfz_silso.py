from __future__ import annotations

import json

from orbitoby.http import SafeHttpClient
from orbitoby.sources.gfz import GFZSource
from orbitoby.sources.silso import SILSOSource


class FakeHTTP:
    def __init__(
        self,
        payload: bytes,
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


def test_gfz_uses_safe_http():
    source = GFZSource()

    assert isinstance(
        source.http,
        SafeHttpClient,
    )

    assert source.http.allowed_hosts == {"kp.gfz.de"}


def test_gfz_fetch_maps_curated_index():
    source = GFZSource()

    fake = FakeHTTP(
        json.dumps(
            {
                "datetime": [],
                "Kp": [],
                "status": [],
            }
        ).encode()
    )

    source.http = fake

    source.fetch(
        "kp",
        start="2024-05-10",
        end="2024-05-11",
    )

    _, kwargs = fake.calls[0]

    assert kwargs["params"]["index"] == "Kp"


def test_gfz_normalizes_parallel_arrays():
    source = GFZSource()

    payload = json.dumps(
        {
            "datetime": [
                "2024-05-10T00:00:00Z",
                "2024-05-10T03:00:00Z",
            ],
            "Kp": [
                2.333,
                3.0,
            ],
            "status": [
                "def",
                "def",
            ],
        }
    ).encode()

    records = source.normalize(
        "kp",
        payload,
        start="2024-05-10",
        end="2024-05-11",
    )

    assert records == [
        {
            "datetime": ("2024-05-10T00:00:00Z"),
            "Kp": 2.333,
            "status": "def",
        },
        {
            "datetime": ("2024-05-10T03:00:00Z"),
            "Kp": 3.0,
            "status": "def",
        },
    ]


def test_gfz_half_open_filter():
    source = GFZSource()

    payload = json.dumps(
        {
            "datetime": [
                "2024-05-10T21:00:00Z",
                "2024-05-11T00:00:00Z",
            ],
            "Kp": [
                4.0,
                5.0,
            ],
        }
    ).encode()

    records = source.normalize(
        "kp",
        payload,
        start="2024-05-10",
        end="2024-05-11",
    )

    assert len(records) == 1
    assert records[0]["Kp"] == 4.0


def test_gfz_definitive_only():
    source = GFZSource()

    fake = FakeHTTP(
        json.dumps(
            {
                "datetime": [],
                "Kp": [],
            }
        ).encode()
    )

    source.http = fake

    source.fetch(
        "kp",
        start="2024-05-10",
        end="2024-05-11",
        status="def",
    )

    _, kwargs = fake.calls[0]

    assert kwargs["params"]["status"] == "def"


def test_silso_daily_csv():
    source = SILSOSource()

    payload = b"2024;5;10;2024.357;136;12.3;31;1\n2024;5;11;2024.360;-1;-1.0;0;0\n"

    records = source.normalize(
        "sunspot_daily",
        payload,
        start="2024-05-10",
        end="2024-05-12",
    )

    assert records[0]["sunspot_number"] == 136

    # Source-native missing sentinel
    # remains untouched at this layer.
    assert records[1]["sunspot_number"] == -1

    assert records[1]["definitive"] == 0


def test_silso_half_open_filter():
    source = SILSOSource()

    payload = b"2024;5;10;2024.357;136;12.3;31;1\n2024;5;11;2024.360;140;10.0;30;1\n"

    records = source.normalize(
        "sunspot_daily",
        payload,
        start="2024-05-10",
        end="2024-05-11",
    )

    assert len(records) == 1
    assert records[0]["day"] == 10


def test_silso_fetch_uses_versioned_file():
    source = SILSOSource()

    fake = FakeHTTP(b"")

    source.http = fake

    source.fetch(
        "sunspot_daily",
        start="2024-05-10",
        end="2024-05-11",
    )

    url, _ = fake.calls[0]

    assert url.endswith("/SILSO/DATA/SN_d_tot_V2.0.csv")


def test_science_sources_skip_identity_store():
    assert not GFZSource().should_index_identity("kp")

    assert not SILSOSource().should_index_identity("sunspot_daily")
