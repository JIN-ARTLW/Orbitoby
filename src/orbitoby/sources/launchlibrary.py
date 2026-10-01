from __future__ import annotations

import json
from typing import Any, ClassVar

from orbitoby.http import SafeHttpClient
from orbitoby.sources.base import SourceAdapter
from orbitoby.sources.metadata import source_metadata


class LaunchLibrarySource(SourceAdapter):
    name = "launchlibrary"

    datasets = (
        "payloads",
        "spacecraft",
        "spacecraft_configurations",
        "launches",
        "agencies",
        "programs",
    )

    BASE_URL = "https://ll.thespacedevs.com/2.3.0"

    ENDPOINTS: ClassVar[dict[str, str]] = {
        "payloads": "/payloads/",
        "spacecraft": "/spacecraft/",
        "spacecraft_configurations": "/spacecraft_configurations/",
        "launches": "/launches/",
        "agencies": "/agencies/",
        "programs": "/programs/",
    }

    def __init__(
        self,
        *,
        http: SafeHttpClient | None = None,
    ) -> None:
        self.metadata = source_metadata(self.name)
        self.http = http or SafeHttpClient(
            allowed_hosts=(self.metadata.host_allowlist),
            read_timeout=60.0,
        )

    def fetch(
        self,
        dataset: str,
        **params: Any,
    ) -> bytes:

        try:
            endpoint = self.ENDPOINTS[dataset]

        except KeyError as exc:
            raise ValueError(f"Unsupported Launch Library dataset: {dataset}") from exc

        url = f"{self.BASE_URL}{endpoint}"

        limit = params.pop(
            "limit",
            100,
        )

        query = {
            "limit": limit,
            **{key: value for key, value in params.items() if value is not None},
        }

        results: list = []

        first_request = True

        while url:
            payload = self.http.get(
                url,
                params=(query if first_request else None),
            )

            data = json.loads(payload)

            first_request = False

            if isinstance(data, dict) and "results" in data:
                results.extend(data["results"])

                url = data.get("next")

            else:
                return payload

        return json.dumps(
            results,
            ensure_ascii=False,
        ).encode("utf-8")

    def normalize(
        self,
        dataset: str,
        payload: bytes,
        **context: Any,
    ) -> list[dict]:

        data = json.loads(payload)

        if isinstance(data, dict):
            return [data]

        if isinstance(data, list):
            return data

        raise RuntimeError("Unexpected Launch Library response.")
