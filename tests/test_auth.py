from orbitoby.auth import CredentialManager


def test_runtime_credentials_have_highest_priority(
    monkeypatch,
):
    monkeypatch.setenv(
        "SPACETRACK_USERNAME",
        "environment-user",
    )

    manager = CredentialManager(
        runtime={
            (
                "spacetrack",
                "username",
            ): "runtime-user",
        }
    )

    result = manager.resolve(
        "spacetrack",
        "username",
    )

    assert result is not None
    assert result.value == "runtime-user"
    assert result.source == "runtime"


def test_environment_credentials(
    monkeypatch,
):
    monkeypatch.setenv(
        "SPACETRACK_USERNAME",
        "environment-user",
    )

    manager = CredentialManager()

    result = manager.resolve(
        "spacetrack",
        "username",
    )

    assert result is not None
    assert result.value == "environment-user"
    assert result.source == "environment"


def test_status_never_contains_secret():
    secret = "do-not-display-this"

    manager = CredentialManager(
        runtime={
            (
                "provider",
                "token",
            ): secret,
        }
    )

    status = manager.status(
        "provider",
        ("token",),
    )

    assert status["token"] == {
        "configured": True,
        "source": "runtime",
    }

    assert secret not in repr(status)


def test_dotenv_is_opt_in(
    tmp_path,
    monkeypatch,
):
    monkeypatch.delenv(
        "DEMO_TOKEN",
        raising=False,
    )

    path = tmp_path / ".env"
    path.write_text(
        "DEMO_TOKEN=from-dotenv\n",
        encoding="utf-8",
    )

    disabled = CredentialManager(
        dotenv_path=path,
        allow_dotenv=False,
    )

    assert (
        disabled.resolve(
            "demo",
            "token",
        )
        is None
    )

    enabled = CredentialManager(
        dotenv_path=path,
        allow_dotenv=True,
    )

    result = enabled.resolve(
        "demo",
        "token",
    )

    assert result is not None
    assert result.value == "from-dotenv"
    assert result.source == "dotenv"
