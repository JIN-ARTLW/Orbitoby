from __future__ import annotations

import json

import pytest

from orbitoby.auth import CredentialManager
from orbitoby.http import SafeHttpClient
from orbitoby.sources.discos import (
    DiscosSource,
)
from orbitoby.sources.registry import (
    build_sources,
)


class FakeHTTP:
    def __init__(
        self,
        payload: bytes = b"{}",
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


def credentials():
    return CredentialManager(
        runtime={
            (
                "discos",
                "token",
            ): "test-discos-token",
        }
    )


def object_payload():
    return json.dumps(
        {
            "data": [
                {
                    "type": "objects",
                    "id": "12345",
                    "attributes": {
                        "satno": 25544,
                        "cosparId": ("1998-067A"),
                        "name": "ISS",
                        "mass": 420000.0,
                        "shape": "Box",
                    },
                    "relationships": {
                        "states": {"links": {"related": ("/api/objects/12345/states")}}
                    },
                }
            ]
        }
    ).encode()


def test_discos_uses_safe_http():
    source = DiscosSource(credentials=credentials())

    assert isinstance(
        source.http,
        SafeHttpClient,
    )


def test_discos_requires_token():
    source = DiscosSource(
        credentials=CredentialManager(),
        http=FakeHTTP(),
    )

    with pytest.raises(
        RuntimeError,
        match="Credential not configured",
    ):
        source.fetch(
            "objects",
            norad_id=25544,
        )


def test_discos_norad_query_contract():
    fake = FakeHTTP(object_payload())

    source = DiscosSource(
        credentials=credentials(),
        http=fake,
    )

    payload = source.fetch(
        "objects",
        norad_id=25544,
    )

    assert payload == fake.payload

    url, kwargs = fake.calls[0]

    assert url == ("https://discosweb.esoc.esa.int/api/objects")

    assert kwargs["params"] == {
        "filter": "eq(satno,25544)",
        "page[size]": "1",
    }

    assert kwargs["headers"]["Authorization"] == ("Bearer test-discos-token")

    assert kwargs["headers"]["DiscosWeb-Api-Version"] == "2"


def test_discos_direct_id_query():
    fake = FakeHTTP(object_payload())

    source = DiscosSource(
        credentials=credentials(),
        http=fake,
    )

    source.fetch(
        "objects",
        discos_id=12345,
    )

    url, kwargs = fake.calls[0]

    assert url == ("https://discosweb.esoc.esa.int/api/objects/12345")

    assert "params" not in kwargs


def test_discos_requires_one_identifier():
    source = DiscosSource(
        credentials=credentials(),
        http=FakeHTTP(),
    )

    with pytest.raises(ValueError):
        source.fetch("objects")

    with pytest.raises(ValueError):
        source.fetch(
            "objects",
            norad_id=25544,
            discos_id=12345,
        )


def test_discos_normalize_preserves_attributes():
    source = DiscosSource(credentials=credentials())

    records = source.normalize(
        "objects",
        object_payload(),
    )

    assert len(records) == 1

    record = records[0]

    assert record["satno"] == 25544
    assert record["cosparId"] == "1998-067A"
    assert record["mass"] == 420000.0
    assert record["shape"] == "Box"

    assert record["discos_id"] == "12345"

    assert record["provider_type"] == "objects"

    assert "provider_relationships" in record


def test_discos_null_data_is_empty():
    source = DiscosSource(credentials=credentials())

    payload = json.dumps(
        {
            "data": None,
        }
    ).encode()

    assert (
        source.normalize(
            "objects",
            payload,
        )
        == []
    )


def test_registry_injects_discos_credentials(
    tmp_path,
):
    manager = credentials()

    sources = build_sources(
        settings_path=(tmp_path / "settings.json"),
        credentials=manager,
    )

    assert isinstance(
        sources["discos"],
        DiscosSource,
    )

    assert sources["discos"].credentials is manager
