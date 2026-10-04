"""Bounded, secret-free repository diagnostic; not an installed Orbitoby CLI."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import requests

from orbitoby import Archive
from orbitoby.auth import CredentialManager
from orbitoby.config import DATA_DIR
from orbitoby.sources.registry import build_sources

PROBES = (
    "celestrak",
    "gfz",
    "nrcan",
    "wdc_kyoto",
    "cdaweb",
    "swarm",
    "noaa",
    "spacetrack",
    "discos",
)
APIS = (
    "datasets",
    "dataset_info",
    "timeseries",
    "window",
    "plot",
    "objects",
    "orbit",
    "orbit_summary",
    "msis_inputs",
    "msis_density",
)


def classify_error(exc):
    """Return fixed labels only; exception text can contain secrets."""
    if isinstance(exc, requests.HTTPError):
        code = exc.response.status_code if exc.response is not None else 0
        if code in (401, 403):
            return "FAIL authentication_or_access_denied"
        return f"FAIL provider_http_{code}"
    if isinstance(exc, requests.Timeout):
        return "WARN network_timeout"
    if isinstance(exc, requests.ConnectionError):
        return "WARN network_connection"
    if isinstance(exc, RuntimeError) and (
        "login" in str(exc).lower() or "authentication" in str(exc).lower()
    ):
        return "FAIL authentication_or_session"
    return "FAIL provider_or_local_error"


def exit_code(results, *, strict=False):
    has_fail = any(value.startswith("FAIL") for value in results)

    has_warn = any(value.startswith("WARN") for value in results)

    return int(has_fail or (strict and has_warn))


def probe(name, allow_dotenv=False):
    manager = CredentialManager(
        allow_dotenv=allow_dotenv,
        dotenv_path=Path(__file__).resolve().parents[1] / ".env",
    )
    required = {
        "spacetrack": (
            ("username", "SPACETRACK_USERNAME"),
            ("password", "SPACETRACK_PASSWORD"),
        ),
        "discos": (("token", "ORBITOBY_DISCOS_TOKEN"),),
    }
    if any(
        not manager.get(name, key, env_name=env) for key, env in required.get(name, ())
    ):
        return "SKIP credential_not_configured"
    try:
        adapter = build_sources(credentials=manager)[name]
        if name in ("wdc_kyoto", "cdaweb", "swarm"):
            payload = adapter.http.get(adapter.BASE_URL + "/capabilities")
        else:
            dataset, params = {
                "celestrak": ("satcat", {"norad_id": 25544}),
                "gfz": ("kp", {"start": date(2024, 5, 10), "end": date(2024, 5, 11)}),
                "nrcan": ("f107_measurements", {}),
                "noaa": ("kp_recent", {}),
                "spacetrack": (
                    "gp_history",
                    {
                        "norad_id": 25544,
                        "start": date(2024, 5, 10),
                        "end": date(2024, 5, 10),
                    },
                ),
                "discos": ("objects", {"norad_id": 25544}),
            }[name]
            payload = adapter.fetch(dataset, **params)
            adapter.normalize(dataset, payload, **params)
        return "PASS endpoint_response" if payload else "FAIL empty_response"
    except Exception as exc:  # noqa: BLE001
        return classify_error(exc)


def run_probe(name, *, allow_dotenv, timeout):
    command = [sys.executable, str(Path(__file__).resolve()), "--probe", name]
    if allow_dotenv:
        command.append("--allow-dotenv")
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired:
        return "WARN deadline_exceeded"
    # Only fixed status output from the worker is admitted. Never relay stderr.
    allowed = {
        "PASS endpoint_response",
        "SKIP credential_not_configured",
        "FAIL empty_response",
        "WARN network_timeout",
        "WARN network_connection",
        "FAIL authentication_or_access_denied",
        "FAIL authentication_or_session",
        "FAIL provider_or_local_error",
    }
    line = result.stdout.strip()
    if line in allowed or (
        line.startswith("FAIL provider_http_")
        and line.removeprefix("FAIL provider_http_").isdigit()
    ):
        return line
    return "FAIL worker_error"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-dotenv", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument(
        "--strict",
        action="store_true",
        help=("Treat WARN diagnostic results as a non-zero exit."),
    )
    parser.add_argument("--probe", choices=PROBES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("timeout must be positive")
    if args.probe:
        print(probe(args.probe, args.allow_dotenv))
        return 0
    results = []
    try:
        with Archive() as archive:
            count = len(archive.sources_available())
            print(f"PASS registered_sources={count}")
            if not all(callable(getattr(archive, name, None)) for name in APIS):
                raise RuntimeError("missing API")
            archive.con.execute("CREATE TEMP TABLE connection_probe(value INTEGER)")
            archive.con.execute("INSERT INTO connection_probe VALUES (1)")
            assert archive.con.execute(
                "SELECT value FROM connection_probe"
            ).fetchone() == (1,)
            with tempfile.TemporaryFile(dir=DATA_DIR) as stream:
                stream.write(b"orbitoby-probe")
            print("PASS public_api_and_local_storage")
    except Exception:  # noqa: BLE001
        results.append("FAIL local_api_or_storage")
        print(results[-1])
    if args.offline:
        print("SKIP network offline_requested")
    else:
        with ThreadPoolExecutor(max_workers=4) as pool:
            statuses = pool.map(
                lambda name: run_probe(
                    name, allow_dotenv=args.allow_dotenv, timeout=args.timeout
                ),
                PROBES,
            )
            for name, status in zip(PROBES, statuses, strict=True):
                results.append(status)
                print(f"{status} source={name}")
    return exit_code(
        results,
        strict=args.strict,
    )


if __name__ == "__main__":
    raise SystemExit(main())
