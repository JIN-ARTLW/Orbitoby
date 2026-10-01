import pytest

from orbitoby.http import SafeHttpClient


def client():
    return SafeHttpClient(
        allowed_hosts={
            "example.com",
        },
        retries=0,
    )


def test_secure_http_accepts_allowed_https():
    assert (
        client().validate_url("https://example.com/data") == "https://example.com/data"
    )


def test_secure_http_rejects_plain_http():
    with pytest.raises(
        ValueError,
        match="HTTPS",
    ):
        client().validate_url("http://example.com/data")


def test_secure_http_rejects_unknown_host():
    with pytest.raises(
        ValueError,
        match="Host not allowed",
    ):
        client().validate_url("https://evil.example/data")


def test_secure_http_rejects_url_credentials():
    with pytest.raises(
        ValueError,
        match="Credentials",
    ):
        client().validate_url("https://user:pass@example.com/data")


def test_sensitive_headers_removed_on_cross_host():
    result = client()._strip_sensitive_headers(
        {
            "Authorization": "secret",
            "Cookie": "secret",
            "X-Test": "safe",
        }
    )

    assert result == {"X-Test": "safe"}
