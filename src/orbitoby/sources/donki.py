from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, ClassVar

from orbitoby.auth import CredentialManager
from orbitoby.http import SafeHttpClient
from orbitoby.sources.base import SourceAdapter
from orbitoby.sources.metadata import source_metadata


@dataclass(frozen=True, slots=True)
class DONKIAPIProfile:
    """Versioned upstream transport contract for NASA CCMC DONKI."""

    revision: str
    base_url: str


CURRENT_DONKI_API = DONKIAPIProfile(
    revision="2026-09-30",
    base_url="https://ccmc.gsfc.nasa.gov/DONKI-API/get",
)


class DONKISource(SourceAdapter):
    """NASA DONKI space-weather event and analysis API.

    Orbitoby exposes half-open, UTC, whole-day intervals:
    [start, end).

    DONKI's API uses inclusive date endpoints, so Orbitoby converts
    the exclusive end boundary to the previous calendar day.
    """

    name = "donki"

    ENDPOINTS: ClassVar[dict[str, str]] = {
        "cme": "CME",
        "cme_analysis": "CMEAnalysis",
        "geomagnetic_storm": "GST",
        "interplanetary_shock": "IPS",
        "solar_flare": "FLR",
        "sep": "SEP",
        "magnetopause_crossing": "MPC",
        "radiation_belt_enhancement": "RBE",
        "high_speed_stream": "HSS",
        "wsa_enlil": "WSAEnlilSimulations",
        "notifications": "notifications",
    }

    datasets = tuple(ENDPOINTS)

    _CME_ANALYSIS_PARAMS: ClassVar[dict[str, str]] = {
        "most_accurate_only": ("mostAccurateOnly"),
        "complete_entry_only": ("completeEntryOnly"),
        "speed": "speed",
        "half_angle": "halfAngle",
        "catalog": "catalog",
        "keyword": "keyword",
    }

    _IPS_PARAMS: ClassVar[dict[str, str]] = {
        "location": "location",
        "catalog": "catalog",
    }

    def __init__(
        self,
        *,
        credentials: CredentialManager | None = None,
        http: SafeHttpClient | None = None,
        api_profile: DONKIAPIProfile | None = None,
    ) -> None:
        self.metadata = source_metadata(self.name)

        # Kept temporarily for source-constructor compatibility.
        # The current CCMC public DONKI data API requires no credentials.
        del credentials

        self.api_profile = api_profile or CURRENT_DONKI_API

        self.http = http or SafeHttpClient(
            allowed_hosts=self.metadata.host_allowlist,
            read_timeout=120.0,
        )

    @staticmethod
    def _whole_day(
        value: str | date | datetime,
        *,
        name: str,
    ) -> date:
        if isinstance(
            value,
            datetime,
        ):
            result = value

            if result.tzinfo is None:
                result = result.replace(tzinfo=UTC)
            else:
                result = result.astimezone(UTC)

            if result.time() != time(
                0,
                0,
            ):
                raise ValueError(f"{name} must be a whole UTC-day boundary for DONKI.")

            return result.date()

        if isinstance(
            value,
            date,
        ):
            return value

        if not isinstance(
            value,
            str,
        ):
            raise TypeError(f"{name} must be str, date, or datetime")

        text = value.strip()

        if not text:
            raise ValueError(f"{name} must not be empty")

        try:
            return date.fromisoformat(text)
        except ValueError:
            pass

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        try:
            result = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"{name} is not a valid ISO-8601 date/time") from exc

        if result.tzinfo is None:
            result = result.replace(tzinfo=UTC)
        else:
            result = result.astimezone(UTC)

        if result.time() != time(
            0,
            0,
        ):
            raise ValueError(f"{name} must be a whole UTC-day boundary for DONKI.")

        return result.date()

    @staticmethod
    def _bool_text(
        value: Any,
        *,
        name: str,
    ) -> str:
        if not isinstance(
            value,
            bool,
        ):
            raise TypeError(f"{name} must be bool")

        return "true" if value else "false"

    def fetch(
        self,
        dataset: str,
        **params: Any,
    ) -> bytes:
        try:
            endpoint = self.ENDPOINTS[dataset]
        except KeyError as exc:
            raise ValueError(f"Unsupported DONKI dataset: {dataset!r}") from exc

        start = params.pop(
            "start",
            None,
        )

        end = params.pop(
            "end",
            None,
        )

        if start is None:
            raise ValueError("start is required for DONKI.")

        if end is None:
            raise ValueError("end is required for DONKI.")

        start_date = self._whole_day(
            start,
            name="start",
        )

        end_date = self._whole_day(
            end,
            name="end",
        )

        if start_date >= end_date:
            raise ValueError("start must be before end.")

        day_count = (end_date - start_date).days

        if dataset == "notifications" and day_count > 30:
            raise ValueError(
                "DONKI notifications supports "
                "at most a 30-day Orbitoby "
                "half-open interval per request."
            )

        query: dict[
            str,
            str | int | float,
        ] = {
            "startDate": start_date.isoformat(),
            "endDate": (end_date - timedelta(days=1)).isoformat(),
        }

        allowed: dict[
            str,
            str,
        ] = {}

        if dataset == "cme_analysis":
            allowed = self._CME_ANALYSIS_PARAMS

        elif dataset == ("interplanetary_shock"):
            allowed = self._IPS_PARAMS

        elif dataset == "notifications":
            allowed = {
                "type": "type",
            }

        unknown = set(params) - set(allowed)

        if unknown:
            raise ValueError(
                "Unsupported DONKI parameter(s) "
                f"for {dataset}: " + ", ".join(sorted(unknown))
            )

        for local_name, remote_name in allowed.items():
            if local_name not in params:
                continue

            value = params[local_name]

            if local_name in {
                "most_accurate_only",
                "complete_entry_only",
            }:
                query[remote_name] = self._bool_text(
                    value,
                    name=local_name,
                )

            else:
                query[remote_name] = value

        return self.http.get(
            f"{self.api_profile.base_url}/{endpoint}",
            params=query,
        )

    def normalize(
        self,
        dataset: str,
        payload: bytes,
        **context: Any,
    ) -> list[dict]:
        del context

        if dataset not in self.ENDPOINTS:
            raise ValueError(f"Unsupported DONKI dataset: {dataset!r}")

        try:
            data = json.loads(payload)
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise RuntimeError("NASA DONKI returned invalid JSON.") from exc

        if isinstance(
            data,
            dict,
        ):
            return [dict(data)]

        if not isinstance(
            data,
            list,
        ):
            raise TypeError("NASA DONKI response must be an object or list.")

        if not all(
            isinstance(
                item,
                dict,
            )
            for item in data
        ):
            raise TypeError("NASA DONKI event list must contain objects.")

        return [dict(item) for item in data]
