import pytest

import orbitoby as ob
from orbitoby import _easy_login as easy_login
from orbitoby.auth import CredentialManager


def test_login_verifies_before_storing(monkeypatch, capsys):
    manager = CredentialManager(runtime={})

    monkeypatch.setattr(easy_login, "shared_credentials", lambda: manager)

    entered = iter(["example-user", "TEST_PRIVATE_PASSWORD"])

    monkeypatch.setattr(
        easy_login.getpass,
        "getpass",
        lambda prompt: next(entered),
    )

    verified = []

    def verify(candidate):
        verified.append(candidate.get("spacetrack", "username"))
        assert candidate.get("spacetrack", "password") == "TEST_PRIVATE_PASSWORD"

    monkeypatch.setattr(easy_login, "_verify_spacetrack", verify)

    ob.login("Space-Track")

    assert verified == ["example-user"]
    assert manager.get("spacetrack", "username") == "example-user"

    output = capsys.readouterr().out
    assert "TEST_PRIVATE_PASSWORD" not in output
    assert "example-user" not in output


def test_failed_authentication_does_not_store_secrets(monkeypatch):
    manager = CredentialManager(runtime={})

    monkeypatch.setattr(easy_login, "shared_credentials", lambda: manager)

    entered = iter(["example-user", "PRIVATE_FAILURE_VALUE"])
    monkeypatch.setattr(
        easy_login.getpass,
        "getpass",
        lambda prompt: next(entered),
    )

    def fail(candidate):
        raise RuntimeError("PRIVATE_FAILURE_VALUE")

    monkeypatch.setattr(easy_login, "_verify_spacetrack", fail)

    with pytest.raises(RuntimeError, match="not verified") as exc:
        ob.login("Space-Track")

    assert "PRIVATE_FAILURE_VALUE" not in str(exc.value)
    assert manager._runtime == {}


def test_unsupported_provider_rejected_before_prompt(monkeypatch):
    def no_prompt(prompt):
        raise AssertionError("Must not prompt for unknown provider")

    monkeypatch.setattr(easy_login.getpass, "getpass", no_prompt)

    with pytest.raises(ValueError, match="not yet supported"):
        ob.login("Unknown-Provider")


def test_existing_credentials_are_reused(monkeypatch):
    manager = CredentialManager(
        runtime={
            ("spacetrack", "username"): "existing-user",
            ("spacetrack", "password"): "existing-secret",
        }
    )

    monkeypatch.setattr(easy_login, "shared_credentials", lambda: manager)

    monkeypatch.setattr(
        easy_login.getpass,
        "getpass",
        lambda prompt: pytest.fail("Should not prompt"),
    )

    checked = []

    def verify(candidate):
        checked.append(candidate.get("spacetrack", "username"))

    monkeypatch.setattr(easy_login, "_verify_spacetrack", verify)

    ob.login("Space-Track")

    assert checked == ["existing-user"]


def test_study_injects_shared_credentials(monkeypatch):
    from orbitoby import service

    manager = CredentialManager(runtime={})

    monkeypatch.setattr(easy_login, "shared_credentials", lambda: manager)

    class FakeArchive:
        def __init__(self, *, credentials):
            self.credentials = credentials

    monkeypatch.setattr(service, "Archive", FakeArchive)

    study = ob.study("2024-05-10", "2024-05-11")

    assert study._core.credentials is manager
