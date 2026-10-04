from __future__ import annotations

import json

import pytest
import requests

from orbitoby.http import SafeHttpClient
from orbitoby.sources.cdaweb import (
    CDAWebSource,
)


def test_connection_error_is_not_retried_by_outer_body_loop(
    monkeypatch,
):
    session = requests.Session()
    calls = 0

    def fail(*args, **kwargs):
        nonlocal calls
        calls += 1

        raise requests.ConnectionError("offline")

    monkeypatch.setattr(
        session,
        "request",
        fail,
    )

    client = SafeHttpClient(
        allowed_hosts=("example.com",),
        retries=3,
        session=session,
    )

    with pytest.raises(requests.ConnectionError):
        client.get("https://example.com/data")

    # urllib3 owns transport retry policy.
    # The outer body loop must not multiply it.
    assert calls == 1


def test_hapi_has_separate_fast_metadata_client():
    source = CDAWebSource()

    assert source.http is not (source.metadata_http)

    assert source.metadata_http.timeout == (
        2.5,
        5.0,
    )

    assert source.metadata_http.retries == 0


def test_hapi_info_uses_metadata_client(
    monkeypatch,
):
    source = CDAWebSource()

    payload = json.dumps(
        {
            "HAPI": "2.0",
            "status": {
                "code": 1200,
                "message": "OK",
            },
            "startDate": ("2020-01-01T00:00:00Z"),
            "stopDate": ("2020-01-02T00:00:00Z"),
        }
    ).encode()

    monkeypatch.setattr(
        source.metadata_http,
        "get",
        lambda *args, **kwargs: payload,
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("science-data HTTP client used for metadata")

    monkeypatch.setattr(
        source.http,
        "get",
        forbidden,
    )

    info = source.info("omni_hourly")

    assert info["status"]["code"] == 1200
