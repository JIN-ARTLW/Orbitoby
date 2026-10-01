from __future__ import annotations

from types import SimpleNamespace

import pytest
import requests

from orbitoby.http import SafeHttpClient


class FakeResponse:
    def __init__(
        self,
        *,
        chunks=None,
        error=None,
        status_code=200,
    ):
        self.headers = {}
        self.status_code = status_code
        self._chunks = chunks or []
        self._error = error

    def raise_for_status(self):
        return None

    def iter_content(
        self,
        chunk_size,
    ):
        del chunk_size

        if self._error is not None:
            raise self._error

        yield from self._chunks

    def close(self):
        return None


class FakeSession:
    def __init__(self, responses):
        self.headers = {}
        self.responses = list(responses)
        self.calls = 0

    def mount(
        self,
        prefix,
        adapter,
    ):
        del prefix, adapter

    def request(
        self,
        method,
        url,
        **kwargs,
    ):
        del method, url, kwargs

        response = self.responses[self.calls]

        self.calls += 1

        return response


def test_get_retries_truncated_body(
    monkeypatch,
):
    monkeypatch.setattr(
        "orbitoby.http.time.sleep",
        lambda _: None,
    )

    session = FakeSession(
        [
            FakeResponse(error=(requests.exceptions.ChunkedEncodingError("truncated"))),
            FakeResponse(
                chunks=[
                    b"complete",
                ]
            ),
        ]
    )

    client = SafeHttpClient(
        allowed_hosts=("example.test",),
        retries=1,
        session=session,
    )

    payload = client.get("https://example.test/data")

    assert payload == b"complete"
    assert session.calls == 2


def test_post_does_not_retry_truncated_body(
    monkeypatch,
):
    monkeypatch.setattr(
        "orbitoby.http.time.sleep",
        lambda _: None,
    )

    session = FakeSession(
        [
            FakeResponse(error=(requests.exceptions.ChunkedEncodingError("truncated"))),
            FakeResponse(chunks=[b"unexpected"]),
        ]
    )

    client = SafeHttpClient(
        allowed_hosts=("example.test",),
        retries=3,
        session=session,
    )

    with pytest.raises(requests.exceptions.ChunkedEncodingError):
        client.post(
            "https://example.test/login",
            data={
                "secret": "value",
            },
        )

    assert session.calls == 1


def test_body_retry_keeps_query_params(
    monkeypatch,
):
    monkeypatch.setattr(
        "orbitoby.http.time.sleep",
        lambda _: None,
    )

    calls = []

    class RecordingSession(FakeSession):
        def request(
            self,
            method,
            url,
            **kwargs,
        ):
            calls.append(
                SimpleNamespace(
                    method=method,
                    url=url,
                    kwargs=kwargs,
                )
            )

            return super().request(
                method,
                url,
                **kwargs,
            )

    session = RecordingSession(
        [
            FakeResponse(error=(requests.exceptions.ChunkedEncodingError("truncated"))),
            FakeResponse(chunks=[b"ok"]),
        ]
    )

    client = SafeHttpClient(
        allowed_hosts=("example.test",),
        retries=1,
        session=session,
    )

    assert (
        client.get(
            "https://example.test/data",
            params={
                "dataset": "science",
            },
        )
        == b"ok"
    )

    assert (
        calls[0].kwargs["params"]
        == calls[1].kwargs["params"]
        == {
            "dataset": "science",
        }
    )
