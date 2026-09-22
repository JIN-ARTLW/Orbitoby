from __future__ import annotations

import json
from typing import Any

import requests

from space_object_archive.sources.base import SourceAdapter


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

    BASE_URL = (
        "https://ll.thespacedevs.com/"
        "2.3.0"
    )

    ENDPOINTS = {
        "payloads":
            "/payloads/",

        "spacecraft":
            "/spacecraft/",

        "spacecraft_configurations":
            "/spacecraft_configurations/",

        "launches":
            "/launches/",

        "agencies":
            "/agencies/",

        "programs":
            "/programs/",
    }

    def __init__(self) -> None:
        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent":
                    "space-object-archive/0.1"
            }
        )

    def fetch(
        self,
        dataset: str,
        **params: Any,
    ) -> bytes:

        try:
            endpoint = self.ENDPOINTS[
                dataset
            ]

        except KeyError as exc:
            raise ValueError(
                f"Unsupported Launch Library "
                f"dataset: {dataset}"
            ) from exc

        url = (
            f"{self.BASE_URL}"
            f"{endpoint}"
        )

        limit = params.pop(
            "limit",
            100,
        )

        query = {
            "limit": limit,
            **{
                key: value
                for key, value
                in params.items()
                if value is not None
            },
        }

        results: list = []

        first_request = True

        while url:
            response = self.session.get(
                url,
                params=(
                    query
                    if first_request
                    else None
                ),
                timeout=60,
            )

            response.raise_for_status()

            data = response.json()

            first_request = False

            if (
                isinstance(data, dict)
                and "results" in data
            ):
                results.extend(
                    data["results"]
                )

                url = data.get(
                    "next"
                )

            else:
                return response.content

        return json.dumps(
            results,
            ensure_ascii=False,
        ).encode(
            "utf-8"
        )

    def normalize(
        self,
        dataset: str,
        payload: bytes,
        **context: Any,
    ) -> list[dict]:

        data = json.loads(
            payload
        )

        if isinstance(data, dict):
            return [data]

        if isinstance(data, list):
            return data

        raise RuntimeError(
            "Unexpected Launch Library response."
        )