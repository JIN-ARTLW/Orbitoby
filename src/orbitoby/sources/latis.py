from __future__ import annotations

import csv
import io
import re
from collections.abc import Iterable, Iterator
from datetime import UTC, date, datetime
from typing import Any

from orbitoby.http import SafeHttpClient

_DATASET_RE = re.compile(r"^[A-Za-z0-9_.-]+$")

_VARIABLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.:-]*$")

_INTEGER_RE = re.compile(r"^[+-]?\d+$")

_FLOAT_RE = re.compile(
    r"^[+-]?(?:"
    r"(?:\d+\.\d*)|"
    r"(?:\.\d+)|"
    r"(?:\d+)"
    r")"
    r"(?:[eE][+-]?\d+)?$"
)

_HEADER_UNIT_RE = re.compile(r"^(?P<name>.+?)\s+\((?P<unit>[^()]*)\)$")


class LaTiSClient:
    """Small, provider-agnostic LaTiS data-access client.

    Orbitoby exposes half-open UTC intervals: [start, end).

    LaTiS query operations are passed in provider order:
    selection -> time formatting -> projection -> limit.
    """

    def __init__(
        self,
        *,
        base_url: str,
        allowed_hosts: Iterable[str],
        http: SafeHttpClient | None = None,
        read_timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")

        self.http = (
            http
            if http is not None
            else SafeHttpClient(
                allowed_hosts=allowed_hosts,
                read_timeout=read_timeout,
            )
        )

    @staticmethod
    def _dataset_id(
        dataset: str,
    ) -> str:
        if not isinstance(
            dataset,
            str,
        ):
            raise TypeError("LaTiS dataset must be a string.")

        result = dataset.strip()

        if not result:
            raise ValueError("LaTiS dataset must not be empty.")

        if not _DATASET_RE.fullmatch(result):
            raise ValueError("LaTiS dataset contains unsafe characters.")

        return result

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

    @staticmethod
    def _variables(
        value: Any,
    ) -> tuple[str, ...]:
        if value is None:
            return ()

        if isinstance(
            value,
            str,
        ):
            items = [item.strip() for item in value.split(",") if item.strip()]

        elif isinstance(
            value,
            (bytes, bytearray),
        ):
            raise TypeError("LaTiS variables must be strings.")

        elif isinstance(
            value,
            Iterable,
        ):
            items = []

            for item in value:
                if not isinstance(
                    item,
                    str,
                ):
                    raise TypeError("LaTiS variable names must be strings.")

                item = item.strip()

                if not item:
                    raise ValueError("LaTiS variable names must not be empty.")

                items.append(item)

        else:
            raise TypeError("LaTiS variables must be a string or iterable of strings.")

        for item in items:
            if not _VARIABLE_RE.fullmatch(item):
                raise ValueError(f"LaTiS variable contains unsafe characters: {item!r}")

        # Orbitoby timeseries should retain
        # the independent time coordinate.
        if items and "time" not in items:
            items.insert(
                0,
                "time",
            )

        return tuple(items)

    def _data_url(
        self,
        dataset: str,
        *,
        suffix: str,
    ) -> str:
        dataset = self._dataset_id(dataset)

        if suffix not in {
            "csv",
            "dds",
        }:
            raise ValueError("Unsupported LaTiS suffix.")

        return f"{self.base_url}/dap/{dataset}.{suffix}"

    def fetch_csv(
        self,
        dataset: str,
        *,
        start: str | date | datetime,
        end: str | date | datetime,
        variables: Any = None,
        limit: int | None = None,
    ) -> bytes:
        start_dt = self._datetime_utc(
            start,
            name="start",
        )

        end_dt = self._datetime_utc(
            end,
            name="end",
        )

        if start_dt >= end_dt:
            raise ValueError("start must be before end for half-open LaTiS intervals.")

        start_text = self._format_time(
            start_dt,
            name="start",
        )

        end_text = self._format_time(
            end_dt,
            name="end",
        )

        query = [
            f"time>={start_text}",
            f"time<{end_text}",
            ("formatTime(yyyy-MM-dd'T'HH:mm:ss'Z')"),
        ]

        selected = self._variables(variables)

        if selected:
            query.append("project(" + ",".join(selected) + ")")

        if limit is not None:
            if isinstance(
                limit,
                bool,
            ):
                raise TypeError("limit must be an integer.")

            limit = int(limit)

            if limit <= 0:
                raise ValueError("limit must be > 0")

            query.append(f"limit({limit})")

        return self.http.get(
            self._data_url(
                dataset,
                suffix="csv",
            ),
            params="&".join(query),
        )

    def dds(
        self,
        dataset: str,
    ) -> bytes:
        return self.http.get(
            self._data_url(
                dataset,
                suffix="dds",
            )
        )

    @staticmethod
    def _header_name(
        value: str,
    ) -> str:
        value = value.strip()

        match = _HEADER_UNIT_RE.fullmatch(value)

        if match is not None:
            value = match.group("name").strip()

        if not value:
            raise ValueError("LaTiS CSV contains an empty column name.")

        return value

    @staticmethod
    def _scalar(
        value: str,
    ):
        value = value.strip()

        if value == "":
            return None

        if _INTEGER_RE.fullmatch(value):
            try:
                return int(value)
            except ValueError:
                pass

        if _FLOAT_RE.fullmatch(value):
            try:
                return float(value)
            except ValueError:
                pass

        return value

    @classmethod
    def iter_csv_records(
        cls,
        payload: bytes,
    ) -> Iterator[dict]:
        try:
            text = payload.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise RuntimeError("LaTiS CSV response is not valid UTF-8.") from exc

        reader = csv.reader(
            io.StringIO(
                text,
                newline="",
            )
        )

        try:
            raw_header = next(reader)
        except StopIteration:
            return

        header = [cls._header_name(value) for value in raw_header]

        if len(set(header)) != len(header):
            raise ValueError("LaTiS CSV contains duplicate normalized column names.")

        for row in reader:
            if not row:
                continue

            if all(not value.strip() for value in row):
                continue

            if len(row) != len(header):
                raise ValueError("LaTiS CSV record length does not match its header.")

            yield {
                key: cls._scalar(value)
                for key, value in zip(
                    header,
                    row,
                    strict=True,
                )
            }

    @classmethod
    def normalize_csv(
        cls,
        payload: bytes,
    ) -> list[dict]:
        return list(cls.iter_csv_records(payload))
