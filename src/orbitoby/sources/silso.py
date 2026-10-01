from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime
from typing import Any, ClassVar

from orbitoby.http import SafeHttpClient
from orbitoby.sources.base import SourceAdapter
from orbitoby.sources.metadata import source_metadata


class SILSOSource(SourceAdapter):
    """WDC-SILSO Sunspot Number Version 2 data."""

    name = "silso"
    raw_extension = "csv"

    BASE_URL = "https://www.sidc.be/SILSO/DATA"

    FILES: ClassVar[dict[str, str]] = {
        "sunspot_daily": ("SN_d_tot_V2.0.csv"),
        "sunspot_monthly": ("SN_m_tot_V2.0.csv"),
        "sunspot_monthly_smoothed": ("SN_ms_tot_V2.0.csv"),
    }

    datasets = tuple(FILES)

    def __init__(self) -> None:
        self.metadata = source_metadata(self.name)

        self.http = SafeHttpClient(
            allowed_hosts=(self.metadata.host_allowlist),
            read_timeout=120.0,
            max_bytes=16 * 1024 * 1024,
        )

    def _url(
        self,
        dataset: str,
    ) -> str:
        try:
            filename = self.FILES[dataset]
        except KeyError as exc:
            raise ValueError(f"Unsupported SILSO dataset: {dataset!r}") from exc

        return f"{self.BASE_URL}/{filename}"

    @staticmethod
    def _date_utc(
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

            if text.endswith("Z"):
                text = text[:-1] + "+00:00"

            try:
                result = datetime.fromisoformat(text)
            except ValueError as exc:
                raise ValueError(f"{name} is not a valid ISO date/time") from exc

        else:
            raise TypeError(f"{name} must be str, date, or datetime")

        if result.tzinfo is None:
            result = result.replace(tzinfo=UTC)
        else:
            result = result.astimezone(UTC)

        return result

    def fetch(
        self,
        dataset: str,
        **params: Any,
    ) -> bytes:
        allowed = {
            "start",
            "end",
        }

        unknown = set(params) - allowed

        if unknown:
            raise ValueError(
                "Unsupported SILSO fetch parameter(s): " + ", ".join(sorted(unknown))
            )

        self._url(dataset)

        start = params.get("start")
        end = params.get("end")

        if (
            start is not None
            and end is not None
            and self._date_utc(
                start,
                name="start",
            )
            >= self._date_utc(
                end,
                name="end",
            )
        ):
            raise ValueError("start must be before end.")

        # SILSO publishes versioned static
        # CSV files. Range filtering is local.
        return self.http.get(self._url(dataset))

    @staticmethod
    def _integer(
        value: str,
    ) -> int:
        return int(value.strip())

    @staticmethod
    def _float(
        value: str,
    ) -> float:
        return float(value.strip())

    def _daily_record(
        self,
        row: list[str],
    ) -> dict:
        if len(row) != 8:
            raise ValueError("Unexpected SILSO daily CSV column count.")

        return {
            "year": self._integer(row[0]),
            "month": self._integer(row[1]),
            "day": self._integer(row[2]),
            "decimal_year": self._float(row[3]),
            "sunspot_number": (self._integer(row[4])),
            "standard_deviation": (self._float(row[5])),
            "observations": (self._integer(row[6])),
            "definitive": (self._integer(row[7])),
        }

    def _monthly_record(
        self,
        row: list[str],
    ) -> dict:
        if len(row) != 7:
            raise ValueError("Unexpected SILSO monthly CSV column count.")

        return {
            "year": self._integer(row[0]),
            "month": self._integer(row[1]),
            "decimal_year": self._float(row[2]),
            "sunspot_number": (self._float(row[3])),
            "standard_deviation": (self._float(row[4])),
            "observations": (self._integer(row[5])),
            "definitive": (self._integer(row[6])),
        }

    def normalize(
        self,
        dataset: str,
        payload: bytes,
        **context: Any,
    ) -> list[dict]:
        self._url(dataset)

        try:
            text = payload.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise RuntimeError("SILSO CSV is not valid UTF-8.") from exc

        start = context.get("start")
        end = context.get("end")

        start_dt = (
            self._date_utc(
                start,
                name="start",
            )
            if start is not None
            else None
        )

        end_dt = (
            self._date_utc(
                end,
                name="end",
            )
            if end is not None
            else None
        )

        reader = csv.reader(
            io.StringIO(
                text,
                newline="",
            ),
            delimiter=";",
        )

        records = []

        for row in reader:
            if not row:
                continue

            if dataset == "sunspot_daily":
                record = self._daily_record(row)

                timestamp = datetime(
                    record["year"],
                    record["month"],
                    record["day"],
                    tzinfo=UTC,
                )

            else:
                record = self._monthly_record(row)

                # Calendar month is preserved
                # separately. This timestamp is
                # only for range selection.
                timestamp = datetime(
                    record["year"],
                    record["month"],
                    1,
                    tzinfo=UTC,
                )

            if start_dt is not None and timestamp < start_dt:
                continue

            if end_dt is not None and timestamp >= end_dt:
                continue

            records.append(record)

        return records
