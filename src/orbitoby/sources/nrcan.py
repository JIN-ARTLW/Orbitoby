from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from orbitoby.http import SafeHttpClient
from orbitoby.sources.base import SourceAdapter
from orbitoby.sources.metadata import source_metadata


class NRCanSource(SourceAdapter):
    """Canadian 10.7 cm solar radio flux measurements."""

    name = "nrcan"
    datasets = ("f107_measurements",)
    raw_extension = "txt"

    DATA_URL = (
        "https://spaceweather.gc.ca/solar_flux_data/daily_flux_values/fluxtable.txt"
    )

    def __init__(self) -> None:
        self.metadata = source_metadata(self.name)

        self.http = SafeHttpClient(
            allowed_hosts=(self.metadata.host_allowlist),
            read_timeout=120.0,
            max_bytes=16 * 1024 * 1024,
        )

    @staticmethod
    def _datetime_utc(
        value: str | date | datetime,
        *,
        name: str,
    ) -> datetime:
        if isinstance(
            value,
            datetime,
        ):
            result = value

        elif isinstance(
            value,
            date,
        ):
            result = datetime(
                value.year,
                value.month,
                value.day,
                tzinfo=UTC,
            )

        elif isinstance(
            value,
            str,
        ):
            text = value.strip()

            if not text:
                raise ValueError(f"{name} must not be empty")

            if text.endswith("Z"):
                text = text[:-1] + "+00:00"

            try:
                result = datetime.fromisoformat(text)
            except ValueError as exc:
                raise ValueError(f"{name} is not a valid ISO-8601 date/time") from exc

        else:
            raise TypeError(f"{name} must be str, date, or datetime")

        if result.tzinfo is None:
            result = result.replace(tzinfo=UTC)
        else:
            result = result.astimezone(UTC)

        return result

    @staticmethod
    def _measurement_time(
        fluxdate: str,
        fluxtime: str,
    ) -> datetime:
        fluxdate = fluxdate.strip()
        fluxtime = fluxtime.strip()

        if len(fluxdate) != 8:
            raise ValueError("Invalid NRCan flux date.")

        if len(fluxtime) != 6:
            raise ValueError("Invalid NRCan flux time.")

        try:
            return datetime(
                int(fluxdate[0:4]),
                int(fluxdate[4:6]),
                int(fluxdate[6:8]),
                int(fluxtime[0:2]),
                int(fluxtime[2:4]),
                int(fluxtime[4:6]),
                tzinfo=UTC,
            )
        except ValueError as exc:
            raise ValueError("Invalid NRCan measurement date/time.") from exc

    def fetch(
        self,
        dataset: str,
        **params: Any,
    ) -> bytes:
        if dataset != "f107_measurements":
            raise ValueError(f"Unsupported NRCan dataset: {dataset!r}")

        allowed = {
            "start",
            "end",
        }

        unknown = set(params) - allowed

        if unknown:
            raise ValueError(
                "Unsupported NRCan fetch parameter(s): " + ", ".join(sorted(unknown))
            )

        start = params.get("start")

        end = params.get("end")

        if (
            start is not None
            and end is not None
            and self._datetime_utc(
                start,
                name="start",
            )
            >= self._datetime_utc(
                end,
                name="end",
            )
        ):
            raise ValueError("start must be before end.")

        # The official archive is one
        # static text table. Orbitoby
        # preserves it raw and filters
        # the requested interval locally.
        return self.http.get(self.DATA_URL)

    def normalize(
        self,
        dataset: str,
        payload: bytes,
        **context: Any,
    ) -> list[dict]:
        if dataset != "f107_measurements":
            raise ValueError(f"Unsupported NRCan dataset: {dataset!r}")

        try:
            text = payload.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise RuntimeError("NRCan F10.7 archive is not valid UTF-8.") from exc

        start = context.get("start")

        end = context.get("end")

        start_dt = (
            self._datetime_utc(
                start,
                name="start",
            )
            if start is not None
            else None
        )

        end_dt = (
            self._datetime_utc(
                end,
                name="end",
            )
            if end is not None
            else None
        )

        records = []

        for line_number, line in enumerate(
            text.splitlines(),
            start=1,
        ):
            line = line.strip()

            if not line:
                continue

            if line.startswith("fluxdate"):
                continue

            if line.startswith("----------"):
                continue

            fields = line.split()

            if len(fields) != 7:
                raise ValueError(
                    f"Unexpected NRCan F10.7 record at line {line_number}."
                )

            (
                fluxdate,
                fluxtime,
                julian_day,
                carrington,
                observed,
                adjusted,
                series_d,
            ) = fields

            timestamp = self._measurement_time(
                fluxdate,
                fluxtime,
            )

            if start_dt is not None and timestamp < start_dt:
                continue

            if end_dt is not None and timestamp >= end_dt:
                continue

            records.append(
                {
                    "time": (
                        timestamp.isoformat().replace(
                            "+00:00",
                            "Z",
                        )
                    ),
                    "julian_day": float(julian_day),
                    "carrington_rotation": float(carrington),
                    "f107_observed": float(observed),
                    "f107_adjusted": float(adjusted),
                    "f107_series_d": float(series_d),
                    "unit": "sfu",
                }
            )

        return records
