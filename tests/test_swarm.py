import json

from orbitoby.http import SafeHttpClient
from orbitoby.sources.registry import build_sources
from orbitoby.sources.swarm import SwarmSource


class FakeHTTP:
    def __init__(self, payload=b"{}"):
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


def hapi_density_payload():
    return json.dumps(
        {
            "HAPI": "3.0",
            "status": {
                "code": 1200,
                "message": "OK",
            },
            "parameters": [
                {
                    "name": "Timestamp",
                    "type": "isotime",
                },
                {
                    "name": "Latitude_GD",
                    "type": "double",
                },
                {
                    "name": "Longitude_GD",
                    "type": "double",
                },
                {
                    "name": "Height_GD",
                    "type": "double",
                },
                {
                    "name": "local_solar_time",
                    "type": "double",
                },
                {
                    "name": "density",
                    "type": "double",
                },
            ],
            "data": [
                [
                    "2015-01-01T00:00:00.000Z",
                    51.72,
                    -147.15,
                    459000.0,
                    12.5,
                    1.16e-12,
                ],
            ],
        }
    ).encode()


def test_swarm_uses_safe_http():
    source = SwarmSource()

    assert isinstance(
        source.http,
        SafeHttpClient,
    )


def test_swarm_curated_profiles():
    source = SwarmSource()

    assert source.remote_dataset_id("density_a_acc") == "SW_OPER_DNSAACC_2_"

    assert source.remote_dataset_id("density_c_pod") == "SW_OPER_DNSCPOD_2_"

    assert len(source.datasets) == 6


def test_swarm_uses_hapi3_request_contract():
    source = SwarmSource()

    fake = FakeHTTP(hapi_density_payload())
    source.http = fake

    payload = source.fetch(
        "density_a_acc",
        start="2015-01-01T00:00:00Z",
        end="2015-01-01T00:01:00Z",
    )

    assert payload == fake.payload

    url, kwargs = fake.calls[0]

    assert url == ("https://vires.services/hapi/data")

    assert kwargs["params"]["dataset"] == ("SW_OPER_DNSAACC_2_")

    assert kwargs["params"]["start"] == ("2015-01-01T00:00:00Z")

    assert kwargs["params"]["stop"] == ("2015-01-01T00:01:00Z")


def test_swarm_preserves_provider_density_fields():
    source = SwarmSource()

    records = source.normalize(
        "density_a_acc",
        hapi_density_payload(),
    )

    assert len(records) == 1

    record = records[0]

    assert record["Timestamp"] == ("2015-01-01T00:00:00.000Z")

    assert record["density"] == 1.16e-12
    assert record["Height_GD"] == 459000.0

    assert "thermosphere_density_modeled" not in record


def test_swarm_skips_identity_store():
    source = SwarmSource()

    assert not source.should_index_identity("density_a_acc")


def test_registry_contains_swarm(
    tmp_path,
):
    sources = build_sources(settings_path=(tmp_path / "settings.json"))

    assert isinstance(
        sources["swarm"],
        SwarmSource,
    )


def test_swarm_requests_hapi_header():
    source = SwarmSource()

    fake = FakeHTTP(hapi_density_payload())
    source.http = fake

    source.fetch(
        "density_a_acc",
        start="2015-01-01T00:00:00Z",
        end="2015-01-01T00:01:00Z",
    )

    _, kwargs = fake.calls[0]

    assert kwargs["params"]["include"] == "header"
