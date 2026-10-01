from datetime import date
from types import SimpleNamespace

import pytest

from orbitoby import config
from orbitoby.auth import (
    CredentialManager,
    default_credential_manager,
)
from orbitoby.http import SafeHttpClient
from orbitoby.sources.celestrak import (
    CelesTrakSource,
)
from orbitoby.sources.gcat import GCATSource
from orbitoby.sources.launchlibrary import (
    LaunchLibrarySource,
)
from orbitoby.sources.noaa import NoaaSource
from orbitoby.sources.registry import (
    build_sources,
)
from orbitoby.sources.satnogs import (
    SatNOGSSource,
)
from orbitoby.sources.spacetrack import (
    SpaceTrackSource,
)


@pytest.mark.parametrize(
    "source_class",
    [
        CelesTrakSource,
        GCATSource,
        NoaaSource,
        SatNOGSSource,
        LaunchLibrarySource,
    ],
)
def test_public_builtin_sources_use_safe_http(
    source_class,
):
    source = source_class()

    assert isinstance(
        source.http,
        SafeHttpClient,
    )

    assert source.http.allowed_hosts == set(source.metadata.host_allowlist)


def test_spacetrack_uses_safe_http():
    source = SpaceTrackSource(
        credentials=CredentialManager(
            runtime={
                (
                    "spacetrack",
                    "username",
                ): "user",
                (
                    "spacetrack",
                    "password",
                ): "secret",
            }
        )
    )

    assert isinstance(
        source.http,
        SafeHttpClient,
    )


def test_default_dotenv_is_disabled(
    monkeypatch,
):
    monkeypatch.delenv(
        "ORBITOBY_ALLOW_DOTENV",
        raising=False,
    )

    manager = default_credential_manager()

    assert manager.allow_dotenv is False


@pytest.mark.parametrize(
    "value",
    [
        "1",
        "true",
        "YES",
        "on",
    ],
)
def test_dotenv_requires_explicit_opt_in(
    monkeypatch,
    value,
):
    monkeypatch.setenv(
        "ORBITOBY_ALLOW_DOTENV",
        value,
    )

    manager = default_credential_manager()

    assert manager.allow_dotenv is True


def test_config_has_no_spacetrack_secrets():
    assert not hasattr(
        config,
        "SPACETRACK_USERNAME",
    )

    assert not hasattr(
        config,
        "SPACETRACK_PASSWORD",
    )


def test_registry_injects_same_credentials(
    tmp_path,
):
    manager = CredentialManager(
        runtime={
            (
                "spacetrack",
                "username",
            ): "user",
            (
                "spacetrack",
                "password",
            ): "secret",
        }
    )

    sources = build_sources(
        settings_path=(tmp_path / "settings.json"),
        credentials=manager,
    )

    assert sources["spacetrack"].credentials is manager


class FakeSpaceTrackHTTP:
    def __init__(self):
        self.session = SimpleNamespace(cookies={"session": "ok"})

        self.login_data = None

    def post(
        self,
        url,
        *,
        data,
    ):
        self.login_data = data

        return b'{"Login":"Success"}'

    def get(
        self,
        url,
    ):
        return b"[]"


def test_spacetrack_uses_runtime_credentials():
    manager = CredentialManager(
        runtime={
            (
                "spacetrack",
                "username",
            ): "runtime-user",
            (
                "spacetrack",
                "password",
            ): "runtime-secret",
        }
    )

    source = SpaceTrackSource(credentials=manager)

    fake = FakeSpaceTrackHTTP()
    source.http = fake

    payload = source.fetch(
        "gp_history",
        norad_id=228,
        start=date(
            2020,
            1,
            1,
        ),
        end=date(
            2020,
            1,
            2,
        ),
    )

    assert payload == b"[]"

    assert fake.login_data == {
        "identity": ("runtime-user"),
        "password": ("runtime-secret"),
    }
