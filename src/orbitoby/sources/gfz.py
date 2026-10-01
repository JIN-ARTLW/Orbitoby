from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Any, ClassVar

from orbitoby.http import SafeHttpClient
from orbitoby.sources.base import SourceAdapter
from orbitoby.sources.metadata import source_metadata


class GFZSource(SourceAdapter):
    """GFZ geomagnetic and solar-index web service."""

    name = "gfz"
    raw_extension = "json"

    BASE_URL = "https://kp.gfz.de/app/json/"

    PROFILES: ClassVar[dict[str, str]] = {
        "kp": "Kp",
        "ap": "ap",
        "ap_daily": "Ap",
        "cp": "Cp",
        "c9": "C9",
        "hp30": "Hp30",
        "hp60": "Hp60",
        "ap30": "ap30",
        "ap60": "ap60",
        "sunspot": "SN",
        "f107_observed": "Fobs",
        "f107_adjusted": "Fadj",
    }

    DEFINITIVE_SUPPORTED = frozenset(
        {
            "Kp",
            "ap",
            "Ap",
            "Cp",
            "C9",
            "SN",
        }
    )

    datasets = tuple(PROFILES)

    def __init__(self) -> None:
        self.metadata = source_metadata(self.name)

        self.http = SafeHttpClient(
            allowed_hosts=(self.metadata.host_allowlist),
            read_timeout=120.0,
        )

    def remote_index(
        self,
        dataset: str,
    ) -> str:
        if not isinstance(
            dataset,
            str,
        ):
            raise TypeError("dataset must be a string")

        dataset = dataset.strip()

        if not dataset:
            raise ValueError("dataset must not be empty")

        if dataset in self.PROFILES:
            return self.PROFILES[dataset]

        if dataset in self.PROFILES.values():
            return dataset

        raise ValueError(f"Unsupported GFZ index: {dataset!r}")

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

    @classmethod
    def _format_time(
        cls,
        value: str | date | datetime,
        *,
        name: str,
    ) -> str:
        result = cls._datetime_utc(
            value,
            name=name,
        )

        timespec = "microseconds" if result.microsecond else "seconds"

        return result.isoformat(timespec=timespec).replace(
            "+00:00",
            "Z",
        )

    def fetch(
        self,
        dataset: str,
        **params: Any,
    ) -> bytes:
        allowed = {
            "start",
            "end",
            "status",
        }

        unknown = set(params) - allowed

        if unknown:
            raise ValueError(
                "Unsupported GFZ fetch parameter(s): " + ", ".join(sorted(unknown))
            )

        start = params.get("start")
        end = params.get("end")

        if start is None:
            raise ValueError("start is required for GFZ data.")

        if end is None:
            raise ValueError("end is required for GFZ data.")

        start_dt = self._datetime_utc(
            start,
            name="start",
        )

        end_dt = self._datetime_utc(
            end,
            name="end",
        )

        if start_dt >= end_dt:
            raise ValueError("start must be before end.")

        remote_index = self.remote_index(dataset)

        query = {
            "start": self._format_time(
                start_dt,
                name="start",
            ),
            "end": self._format_time(
                end_dt,
                name="end",
            ),
            "index": remote_index,
        }

        status = params.get("status")

        if status is not None:
            if status != "def":
                raise ValueError("GFZ status currently supports only 'def'.")

            if remote_index not in self.DEFINITIVE_SUPPORTED:
                raise ValueError(
                    f"GFZ definitive-only mode is not documented for {remote_index}."
                )

            query["status"] = "def"

        return self.http.get(
            self.BASE_URL,
            params=query,
        )

    def normalize(
        self,
        dataset: str,
        payload: bytes,
        **context: Any,
    ) -> list[dict]:
        remote_index = self.remote_index(dataset)

        try:
            result = json.loads(payload)
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise RuntimeError("GFZ returned invalid JSON.") from exc

        if not isinstance(
            result,
            dict,
        ):
            raise TypeError("GFZ response must be an object.")

        times = result.get("datetime")

        values = result.get(remote_index)

        if not isinstance(
            times,
            list,
        ):
            raise TypeError("GFZ response has no valid datetime array.")

        if not isinstance(
            values,
            list,
        ):
            raise TypeError(f"GFZ response has no valid {remote_index} array.")

        if len(times) != len(values):
            raise ValueError("GFZ datetime/value arrays have different lengths.")

        statuses = result.get("status")

        if (
            statuses is not None
            and isinstance(
                statuses,
                list,
            )
            and len(statuses) != len(times)
        ):
            raise ValueError("GFZ status array length does not match data.")

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

        for index, (
            timestamp,
            value,
        ) in enumerate(
            zip(
                times,
                values,
                strict=True,
            )
        ):
            timestamp_dt = self._datetime_utc(
                timestamp,
                name="GFZ timestamp",
            )

            if start_dt is not None and timestamp_dt < start_dt:
                continue

            # Orbitoby API uses [start, end).
            if end_dt is not None and timestamp_dt >= end_dt:
                continue

            record = {
                "datetime": timestamp,
                remote_index: value,
            }

            if isinstance(
                statuses,
                list,
            ):
                record["status"] = statuses[index]

            records.append(record)

        return records
