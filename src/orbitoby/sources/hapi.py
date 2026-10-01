from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, date, datetime
from typing import Any, ClassVar, Literal

from orbitoby.http import SafeHttpClient
from orbitoby.sources.base import SourceAdapter
from orbitoby.sources.metadata import source_metadata

HAPIRequestStyle = Literal["2", "3"]


class HAPISource(SourceAdapter):
    """Generic HAPI 2.x / 3.x time-series source.

    Built-in subclasses expose a small curated ``datasets`` tuple while
    still allowing raw provider dataset identifiers to be requested.

    Orbitoby uses half-open UTC intervals: [start, end).
    """

    name = "hapi"

    BASE_URL: ClassVar[str] = ""
    REQUEST_STYLE: ClassVar[HAPIRequestStyle] = "3"
    PROFILES: ClassVar[dict[str, str]] = {}

    def __init__(self) -> None:
        if self.name == "hapi":
            raise TypeError(
                "HAPISource is a protocol base class; "
                "instantiate a provider-specific subclass."
            )

        if not self.BASE_URL:
            raise ValueError("HAPI source requires BASE_URL.")

        self.metadata = source_metadata(self.name)

        self.http = SafeHttpClient(
            allowed_hosts=self.metadata.host_allowlist,
            read_timeout=120.0,
        )

    @property
    def base_url(self) -> str:
        return self.BASE_URL.rstrip("/")

    def _endpoint(
        self,
        name: str,
    ) -> str:
        return f"{self.base_url}/{name}"

    def remote_dataset_id(
        self,
        dataset: str,
    ) -> str:
        if not isinstance(dataset, str):
            raise TypeError("dataset must be a string")

        dataset = dataset.strip()

        if not dataset:
            raise ValueError("dataset must not be empty")

        return self.PROFILES.get(
            dataset,
            dataset,
        )

    @staticmethod
    def _datetime_utc(
        value: str | date | datetime,
        *,
        name: str,
    ) -> datetime:
        if isinstance(value, datetime):
            result = value

        elif isinstance(value, date):
            result = datetime(
                value.year,
                value.month,
                value.day,
                tzinfo=UTC,
            )

        elif isinstance(value, str):
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
    def _format_parameters(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        if isinstance(value, str):
            result = value.strip()

            return result or None

        if isinstance(
            value,
            (bytes, bytearray),
        ):
            raise TypeError("parameters must be a string or iterable of strings")

        if not isinstance(
            value,
            Iterable,
        ):
            raise TypeError("parameters must be a string or iterable of strings")

        items = []

        for item in value:
            if not isinstance(
                item,
                str,
            ):
                raise TypeError("HAPI parameter names must be strings")

            item = item.strip()

            if not item:
                raise ValueError("HAPI parameter names must not be empty")

            items.append(item)

        return ",".join(items) or None

    @staticmethod
    def _decode_response(
        payload: bytes,
        *,
        endpoint: str,
        success_codes: tuple[int, ...] = (1200,),
    ) -> dict:
        try:
            result = json.loads(payload)
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise RuntimeError(f"HAPI {endpoint} returned invalid JSON.") from exc

        if not isinstance(
            result,
            dict,
        ):
            raise TypeError(f"HAPI {endpoint} response must be an object.")

        status = result.get("status")

        if not isinstance(
            status,
            dict,
        ):
            raise TypeError(f"HAPI {endpoint} response has no valid status object.")

        code = status.get("code")

        if not isinstance(
            code,
            int,
        ):
            raise TypeError(f"HAPI {endpoint} response has no integer status code.")

        if code not in success_codes:
            message = status.get(
                "message",
                "unknown HAPI error",
            )

            raise RuntimeError(f"HAPI {endpoint} failed with status {code}: {message}")

        return result

    def capabilities(
        self,
    ) -> dict:
        payload = self.http.get(self._endpoint("capabilities"))

        return self._decode_response(
            payload,
            endpoint="capabilities",
        )

    def catalog(
        self,
    ) -> list[dict]:
        payload = self.http.get(self._endpoint("catalog"))

        result = self._decode_response(
            payload,
            endpoint="catalog",
        )

        catalog = result.get("catalog")

        if not isinstance(
            catalog,
            list,
        ):
            raise TypeError("HAPI catalog response has no valid catalog list.")

        normalized = []

        for entry in catalog:
            if not isinstance(
                entry,
                dict,
            ):
                raise TypeError("HAPI catalog entries must be objects.")

            normalized.append(dict(entry))

        return normalized

    def info(
        self,
        dataset: str,
    ) -> dict:
        remote_id = self.remote_dataset_id(dataset)

        key = "id" if self.REQUEST_STYLE == "2" else "dataset"

        payload = self.http.get(
            self._endpoint("info"),
            params={
                key: remote_id,
            },
        )

        return self._decode_response(
            payload,
            endpoint="info",
        )

    def fetch(
        self,
        dataset: str,
        **params: Any,
    ) -> bytes:
        allowed = {
            "start",
            "end",
            "parameters",
        }

        unknown = set(params) - allowed

        if unknown:
            raise ValueError(
                "Unsupported HAPI fetch parameter(s): " + ", ".join(sorted(unknown))
            )

        start = params.get("start")
        end = params.get("end")

        if start is None:
            raise ValueError("start is required for HAPI data.")

        if end is None:
            raise ValueError("end is required for HAPI data.")

        start_dt = self._datetime_utc(
            start,
            name="start",
        )
        end_dt = self._datetime_utc(
            end,
            name="end",
        )

        if start_dt >= end_dt:
            raise ValueError("start must be before end for half-open HAPI intervals.")

        start_text = self._format_time(
            start_dt,
            name="start",
        )
        end_text = self._format_time(
            end_dt,
            name="end",
        )

        remote_id = self.remote_dataset_id(dataset)

        query: dict[str, str] = {
            "format": "json",
        }

        if self.REQUEST_STYLE == "2":
            query.update(
                {
                    "id": remote_id,
                    "time.min": start_text,
                    "time.max": end_text,
                }
            )

        elif self.REQUEST_STYLE == "3":
            query.update(
                {
                    "dataset": remote_id,
                    "start": start_text,
                    "stop": end_text,
                }
            )

        else:
            raise RuntimeError(
                f"Unsupported HAPI request style: {self.REQUEST_STYLE!r}"
            )

        parameters = self._format_parameters(params.get("parameters"))

        if parameters is not None:
            query["parameters"] = parameters

        return self.http.get(
            self._endpoint("data"),
            params=query,
        )

    def normalize(
        self,
        dataset: str,
        payload: bytes,
        **context: Any,
    ) -> list[dict]:
        self.remote_dataset_id(dataset)

        result = self._decode_response(
            payload,
            endpoint="data",
            success_codes=(
                1200,
                1201,
            ),
        )

        status = result["status"]

        if status["code"] == 1201:
            return []

        parameters = result.get("parameters")

        data = result.get(
            "data",
            [],
        )

        if not isinstance(
            parameters,
            list,
        ):
            raise TypeError("HAPI JSON data response has no parameter metadata.")

        if not isinstance(
            data,
            list,
        ):
            raise TypeError("HAPI JSON data field must be a list.")

        names: list[str] = []

        for parameter in parameters:
            if not isinstance(
                parameter,
                dict,
            ):
                raise TypeError("HAPI parameter metadata must be objects.")

            name = parameter.get("name")

            if not isinstance(
                name,
                str,
            ):
                raise TypeError("HAPI parameter metadata has no valid name.")

            names.append(name)

        records = []

        for row in data:
            if not isinstance(
                row,
                list,
            ):
                raise TypeError("HAPI JSON records must be arrays.")

            try:
                record = dict(
                    zip(
                        names,
                        row,
                        strict=True,
                    )
                )
            except ValueError as exc:
                raise ValueError(
                    "HAPI record length does not match parameter metadata."
                ) from exc

            records.append(record)

        return records
