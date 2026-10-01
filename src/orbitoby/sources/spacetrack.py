from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from requests import HTTPError

from orbitoby.auth import (
    CredentialManager,
    default_credential_manager,
)
from orbitoby.http import SafeHttpClient
from orbitoby.sources.base import SourceAdapter
from orbitoby.sources.metadata import source_metadata


class SpaceTrackSource(SourceAdapter):
    """Authenticated Space-Track GP history source."""

    name = "spacetrack"

    datasets = ("gp_history",)

    BASE_URL = "https://www.space-track.org"
    LOGIN_URL = f"{BASE_URL}/ajaxauth/login"

    def __init__(
        self,
        *,
        credentials: CredentialManager | None = None,
    ) -> None:
        self.metadata = source_metadata(self.name)

        self.credentials = credentials or default_credential_manager()

        self.http = SafeHttpClient(
            allowed_hosts=(self.metadata.host_allowlist),
            read_timeout=120.0,
        )

        self._logged_in = False

    def _login(self) -> None:
        if self._logged_in:
            return

        username = self.credentials.get(
            "spacetrack",
            "username",
            env_name=("SPACETRACK_USERNAME"),
            required=True,
        )

        password = self.credentials.get(
            "spacetrack",
            "password",
            env_name=("SPACETRACK_PASSWORD"),
            required=True,
        )

        payload = self.http.post(
            self.LOGIN_URL,
            data={
                "identity": username,
                "password": password,
            },
        )

        try:
            result = json.loads(payload)
        except (
            json.JSONDecodeError,
            UnicodeDecodeError,
        ):
            result = None

        if isinstance(result, dict) and result.get("Login") == "Failed":
            raise RuntimeError(
                "Space-Track login failed. Check credentials and account status."
            )

        if not self.http.session.cookies:
            raise RuntimeError("Space-Track login did not create a session cookie.")

        self._logged_in = True

    def fetch(
        self,
        dataset: str,
        **params: Any,
    ) -> bytes:
        norad_id = params.get("norad_id")
        start = params.get("start")
        end = params.get("end")

        if dataset != "gp_history":
            raise ValueError(f"Unsupported Space-Track dataset: {dataset}")

        if norad_id is None:
            raise ValueError("norad_id is required for gp_history.")

        if start is None or end is None:
            raise ValueError("start and end are required for gp_history.")

        if start > end:
            raise ValueError("start must be <= end")

        self._login()

        query_end = end + timedelta(days=1)

        url = (
            f"{self.BASE_URL}"
            "/basicspacedata/query"
            "/class/gp_history"
            f"/NORAD_CAT_ID/{norad_id}"
            f"/EPOCH/{start.isoformat()}"
            f"--{query_end.isoformat()}"
            "/orderby/EPOCH%20asc"
            "/format/json"
        )

        try:
            payload = self.http.get(url)
        except HTTPError as exc:
            response = exc.response

            if response is not None and response.status_code == 401:
                self._logged_in = False

                raise RuntimeError(
                    "Space-Track returned "
                    "HTTP 401 Unauthorized. "
                    "Authentication failed "
                    "or the session expired."
                ) from exc

            raise

        try:
            parsed = json.loads(payload)
        except (
            json.JSONDecodeError,
            UnicodeDecodeError,
        ) as exc:
            preview = payload[:200].decode(
                "utf-8",
                errors="replace",
            )

            raise RuntimeError(
                "Space-Track returned a "
                "non-JSON response. "
                f"Response preview: "
                f"{preview!r}"
            ) from exc

        if not isinstance(
            parsed,
            list,
        ):
            raise TypeError(f"Unexpected Space-Track response format: {parsed!r}")

        return payload

    def normalize(
        self,
        dataset: str,
        payload: bytes,
        **context: Any,
    ) -> list[dict]:
        del context

        if dataset != "gp_history":
            raise ValueError(f"Unsupported Space-Track dataset: {dataset}")

        raw = json.loads(payload)

        if not isinstance(
            raw,
            list,
        ):
            raise TypeError("Unexpected Space-Track payload format.")

        return [self._normalize_gp(row) for row in raw]

    @staticmethod
    def _to_float(
        value: Any,
    ) -> float | None:
        if value in (
            None,
            "",
        ):
            return None

        return float(value)

    @staticmethod
    def _to_int(
        value: Any,
    ) -> int | None:
        if value in (
            None,
            "",
        ):
            return None

        return int(value)

    @staticmethod
    def _to_datetime(
        value: str | None,
    ) -> datetime | None:
        if not value:
            return None

        value = value.rstrip("Z")

        dt = datetime.fromisoformat(value)

        if dt.tzinfo is not None:
            dt = dt.astimezone(UTC).replace(tzinfo=None)

        return dt

    def _normalize_gp(
        self,
        row: dict,
    ) -> dict:
        return {
            "gp_id": self._to_int(row.get("GP_ID")),
            "norad_id": self._to_int(row.get("NORAD_CAT_ID")),
            "object_id": row.get("OBJECT_ID"),
            "object_name": row.get("OBJECT_NAME"),
            "epoch": self._to_datetime(row.get("EPOCH")),
            "mean_motion": self._to_float(row.get("MEAN_MOTION")),
            "eccentricity": self._to_float(row.get("ECCENTRICITY")),
            "inclination_deg": self._to_float(row.get("INCLINATION")),
            "raan_deg": self._to_float(row.get("RA_OF_ASC_NODE")),
            "arg_pericenter_deg": self._to_float(row.get("ARG_OF_PERICENTER")),
            "mean_anomaly_deg": self._to_float(row.get("MEAN_ANOMALY")),
            "bstar": self._to_float(row.get("BSTAR")),
            "semimajor_axis_km": self._to_float(row.get("SEMIMAJOR_AXIS")),
            "period_min": self._to_float(row.get("PERIOD")),
            "apoapsis_km": self._to_float(row.get("APOAPSIS")),
            "periapsis_km": self._to_float(row.get("PERIAPSIS")),
            "tle_line1": row.get("TLE_LINE1"),
            "tle_line2": row.get("TLE_LINE2"),
        }
