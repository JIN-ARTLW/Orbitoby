from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from orbitoby.config import (
    SPACETRACK_PASSWORD,
    SPACETRACK_USERNAME,
)
from orbitoby.sources.base import SourceAdapter


class SpaceTrackSource(SourceAdapter):
    """
    Space-Track 데이터 소스 adapter.

    현재 지원:
    - gp_history
    """

    name = "spacetrack"

    BASE_URL = "https://www.space-track.org"
    LOGIN_URL = f"{BASE_URL}/ajaxauth/login"

    def __init__(self) -> None:
        self.session = requests.Session()
        self._logged_in = False

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _login(self) -> None:
        """
        Space-Track 계정으로 로그인하고
        requests.Session에 인증 상태를 유지한다.
        """

        if self._logged_in:
            return

        if not SPACETRACK_USERNAME:
            raise RuntimeError(
                "SPACETRACK_USERNAME is not configured."
            )

        if not SPACETRACK_PASSWORD:
            raise RuntimeError(
                "SPACETRACK_PASSWORD is not configured."
            )

        response = self.session.post(
            self.LOGIN_URL,
            data={
                "identity": SPACETRACK_USERNAME,
                "password": SPACETRACK_PASSWORD,
            },
            timeout=30,
        )

        response.raise_for_status()

        # Space-Track은 로그인 실패 시에도 HTTP 200과 함께
        # {"Login": "Failed"}를 반환할 수 있다.
        try:
            result = response.json()
        except ValueError:
            result = None

        if isinstance(result, dict):
            if result.get("Login") == "Failed":
                raise RuntimeError(
                    "Space-Track login failed. "
                    "Check username/password and account status."
                )

        if not self.session.cookies:
            raise RuntimeError(
                "Space-Track login did not create a session cookie."
            )

        self._logged_in = True

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------

    def fetch(
        self,
        dataset: str,
        **params: Any,
    ) -> bytes:
        """
        Space-Track에서 원본 데이터를 가져온다.

        params 예시:
            norad_id=228
            start=date(...)
            end=date(...)
        """

        norad_id = params.get("norad_id")
        start = params.get("start")
        end = params.get("end")

        if dataset != "gp_history":
            raise ValueError(
                f"Unsupported Space-Track dataset: {dataset}"
            )

        if norad_id is None:
            raise ValueError(
                "norad_id is required for gp_history."
            )

        if start is None or end is None:
            raise ValueError(
                "start and end are required for gp_history."
            )

        if start > end:
            raise ValueError(
                "start must be <= end"
            )

        self._login()

        # 마지막 날짜 하루 전체를 포함하기 위해
        # query upper bound를 다음 날로 설정
        query_end = end + timedelta(days=1)

        url = (
            f"{self.BASE_URL}"
            "/basicspacedata/query"
            "/class/gp_history"
            f"/NORAD_CAT_ID/{norad_id}"
            f"/EPOCH/{start.isoformat()}--{query_end.isoformat()}"
            "/orderby/EPOCH%20asc"
            "/format/json"
        )

        response = self.session.get(
            url,
            timeout=120,
        )

        if response.status_code == 401:
            self._logged_in = False

            raise RuntimeError(
                "Space-Track returned HTTP 401 Unauthorized. "
                "Authentication failed or the session expired."
            )

        response.raise_for_status()

        # JSON이 아닌 로그인 페이지나 HTML이 반환되는 경우 탐지
        try:
            parsed = response.json()

        except ValueError as exc:
            preview = response.text[:200]

            raise RuntimeError(
                "Space-Track returned a non-JSON response. "
                f"Response preview: {preview!r}"
            ) from exc

        if not isinstance(parsed, list):
            raise RuntimeError(
                "Unexpected Space-Track response format: "
                f"{parsed!r}"
            )

        return response.content

    # ------------------------------------------------------------------
    # Normalize
    # ------------------------------------------------------------------

    def normalize(
        self,
        dataset: str,
        payload: bytes,
        **context: Any,
    ) -> list[dict]:
        """
        Space-Track raw JSON을
        orbitoby 내부 형식으로 변환한다.
        """

        if dataset != "gp_history":
            raise ValueError(
                f"Unsupported Space-Track dataset: {dataset}"
            )

        raw = json.loads(payload)

        if not isinstance(raw, list):
            raise RuntimeError(
                "Unexpected Space-Track payload format."
            )

        return [
            self._normalize_gp(row)
            for row in raw
        ]

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value in (None, ""):
            return None

        return float(value)

    @staticmethod
    def _to_int(value: Any) -> int | None:
        if value in (None, ""):
            return None

        return int(value)

    @staticmethod
    def _to_datetime(
        value: str | None,
    ) -> datetime | None:
        """
        Space-Track timestamp를 datetime으로 변환한다.
        """

        if not value:
            return None

        value = value.rstrip("Z")

        dt = datetime.fromisoformat(value)

        if dt.tzinfo is not None:
            dt = (
                dt.astimezone(timezone.utc)
                .replace(tzinfo=None)
            )

        return dt

    # ------------------------------------------------------------------
    # GP_HISTORY normalization
    # ------------------------------------------------------------------

    def _normalize_gp(
        self,
        row: dict,
    ) -> dict:
        """
        GP_HISTORY record 하나를
        내부 orbit_elements schema로 변환한다.
        """

        return {
            "gp_id": self._to_int(
                row.get("GP_ID")
            ),

            "norad_id": self._to_int(
                row.get("NORAD_CAT_ID")
            ),

            "object_id": row.get(
                "OBJECT_ID"
            ),

            "object_name": row.get(
                "OBJECT_NAME"
            ),

            "epoch": self._to_datetime(
                row.get("EPOCH")
            ),

            "mean_motion": self._to_float(
                row.get("MEAN_MOTION")
            ),

            "eccentricity": self._to_float(
                row.get("ECCENTRICITY")
            ),

            "inclination_deg": self._to_float(
                row.get("INCLINATION")
            ),

            "raan_deg": self._to_float(
                row.get("RA_OF_ASC_NODE")
            ),

            "arg_pericenter_deg": self._to_float(
                row.get("ARG_OF_PERICENTER")
            ),

            "mean_anomaly_deg": self._to_float(
                row.get("MEAN_ANOMALY")
            ),

            "bstar": self._to_float(
                row.get("BSTAR")
            ),

            "semimajor_axis_km": self._to_float(
                row.get("SEMIMAJOR_AXIS")
            ),

            "period_min": self._to_float(
                row.get("PERIOD")
            ),

            "apoapsis_km": self._to_float(
                row.get("APOAPSIS")
            ),

            "periapsis_km": self._to_float(
                row.get("PERIAPSIS")
            ),

            "tle_line1": row.get(
                "TLE_LINE1"
            ),

            "tle_line2": row.get(
                "TLE_LINE2"
            ),
        }