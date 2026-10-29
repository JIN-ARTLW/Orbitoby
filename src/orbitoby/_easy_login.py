"""Verified, process-local login for beginner workflows."""

import getpass
import re
from functools import lru_cache

from orbitoby.auth import CredentialManager


@lru_cache(maxsize=1)
def shared_credentials():
    """One runtime credential manager shared by Easy API studies."""
    return CredentialManager(allow_dotenv=False)


def _verify_spacetrack(credentials):
    """Authenticate against the provider and verify its session cookie."""
    from orbitoby.sources.spacetrack import SpaceTrackSource

    adapter = SpaceTrackSource(credentials=credentials)

    try:
        adapter._login()
    finally:
        adapter.http.session.close()


def login(provider, *, prompt=False):
    """Verify provider login without printing or persisting secrets."""
    if not isinstance(provider, str):
        raise TypeError("Provider name must be a string.")

    normalized = re.sub(r"[\s_-]+", "", provider.casefold())

    if normalized != "spacetrack":
        raise ValueError(
            f"Interactive login for {provider!r} is not yet supported. "
            'Currently supported: ob.login("Space-Track").'
        )

    if not isinstance(prompt, bool):
        raise TypeError("prompt must be True or False.")

    manager = shared_credentials()

    username = None
    password = None

    if not prompt:
        username = manager.get(
            "spacetrack",
            "username",
            env_name="SPACETRACK_USERNAME",
        )
        password = manager.get(
            "spacetrack",
            "password",
            env_name="SPACETRACK_PASSWORD",
        )

    if not username:
        username = getpass.getpass("Space-Track username (hidden): ").strip()

    if not password:
        password = getpass.getpass("Space-Track password (hidden): ")

    if not username or not password:
        raise ValueError(
            "Space-Track username and password are required. No credentials were saved."
        )

    # Check authentication using a temporary manager first.
    # Failed credentials must not replace the working runtime state.
    candidate = CredentialManager(
        runtime={
            ("spacetrack", "username"): username,
            ("spacetrack", "password"): password,
        },
        allow_dotenv=False,
    )

    try:
        _verify_spacetrack(candidate)
    # Any provider exception may contain sensitive request details.
    # Convert it to a redacted error without preserving the cause.
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Space-Track authentication was not verified "
            f"({type(exc).__name__}). "
            "Check account status, credentials and network access. "
            "New credentials were not stored."
        ) from None

    # Commit only after the remote session was verified.
    manager.set_runtime("spacetrack", "username", username)
    manager.set_runtime("spacetrack", "password", password)

    print("Space-Track authentication verified.")
    print(
        "Orbitoby did not add persistent credential storage. "
        "The Easy API can reuse credentials in this Python process."
    )
