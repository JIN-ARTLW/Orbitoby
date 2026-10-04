import importlib.util
import subprocess
from pathlib import Path

import pytest
import requests

spec = importlib.util.spec_from_file_location(
    "connection_check",
    Path(__file__).resolve().parents[1] / "scripts/check_connections.py",
)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


@pytest.mark.parametrize(
    "statuses,expected",
    [
        (["PASS ok", "SKIP credential_not_configured"], 0),
        (["WARN network_timeout"], 0),
        (["FAIL authentication_or_access_denied"], 1),
    ],
)
def test_exit_policy(statuses, expected):
    assert check.exit_code(statuses) == expected


def test_exception_secret_is_not_printed():
    secret = "DO_NOT_PRINT_SECRET"
    assert secret not in check.classify_error(RuntimeError(secret))
    assert check.classify_error(requests.Timeout(secret)) == "WARN network_timeout"
    response = requests.Response()
    response.status_code = 401
    assert (
        check.classify_error(requests.HTTPError(secret, response=response))
        == "FAIL authentication_or_access_denied"
    )


def test_missing_credential_is_skip(monkeypatch):
    monkeypatch.setattr(check.CredentialManager, "get", lambda *a, **k: None)
    assert check.probe("spacetrack") == "SKIP credential_not_configured"
    assert check.probe("discos") == "SKIP credential_not_configured"


def test_worker_output_is_not_relayed(monkeypatch):
    monkeypatch.setattr(
        check.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess([], 1, "secret", "secret"),
    )
    assert check.run_probe("gfz", allow_dotenv=False, timeout=1) == "FAIL worker_error"


def test_worker_deadline(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("worker", 1)

    monkeypatch.setattr(check.subprocess, "run", timeout)
    assert (
        check.run_probe("gfz", allow_dotenv=False, timeout=1)
        == "WARN deadline_exceeded"
    )


def test_exit_code_strict_rejects_warning():
    assert (
        check.exit_code(
            ["WARN deadline_exceeded"],
            strict=True,
        )
        == 1
    )
