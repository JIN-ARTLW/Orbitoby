from orbitoby.sources.cdaweb import CDAWebSource
from orbitoby.sources.hapi import HAPISource


def test_hapi_default_timeout_policy():
    assert HAPISource.CONNECT_TIMEOUT == 10.0
    assert HAPISource.READ_TIMEOUT == 120.0


def test_cdaweb_provider_timeout_policy():
    source = CDAWebSource()

    assert source.CONNECT_TIMEOUT == 30.0
    assert source.READ_TIMEOUT == 120.0
    assert source.http.timeout == (30.0, 120.0)
