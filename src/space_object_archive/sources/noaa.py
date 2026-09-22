from __future__ import annotations

import json
from typing import Any

import requests

from space_object_archive.sources.base import SourceAdapter


class NoaaSource(SourceAdapter):
    name = "noaa"

    datasets = (
        "solar_cycle",
        "f107_cycle",
        "sunspots",
        "f107_recent",
        "f107_30day",
        "kp_recent",
        "dst_recent",
    )

    URLS = {
        "solar_cycle": (
            "https://services.swpc.noaa.gov/"
            "json/solar-cycle/"
            "observed-solar-cycle-indices.json"
        ),

        "f107_cycle": (
            "https://services.swpc.noaa.gov/"
            "json/solar-cycle/"
            "f10-7cm-flux.json"
        ),

        "sunspots": (
            "https://services.swpc.noaa.gov/"
            "json/solar-cycle/"
            "sunspots.json"
        ),

        "f107_recent": (
            "https://services.swpc.noaa.gov/"
            "json/f107_cm_flux.json"
        ),

        "f107_30day": (
            "https://services.swpc.noaa.gov/"
            "products/10cm-flux-30-day.json"
        ),

        "kp_recent": (
            "https://services.swpc.noaa.gov/"
            "json/planetary_k_index_1m.json"
        ),

        "dst_recent": (
            "https://services.swpc.noaa.gov/"
            "products/kyoto-dst.json"
        ),
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
            url = self.URLS[
                dataset
            ]

        except KeyError as exc:
            raise ValueError(
                f"Unsupported NOAA dataset: "
                f"{dataset}"
            ) from exc

        response = self.session.get(
            url,
            timeout=60,
        )

        response.raise_for_status()

        return response.content

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

            # 일부 NOAA product는
            # [["header1", "header2"], [...], ...]
            # 형태로 제공됨.
            if (
                data
                and isinstance(
                    data[0],
                    list,
                )
            ):
                headers = data[0]

                return [
                    dict(
                        zip(
                            headers,
                            row,
                            strict=False,
                        )
                    )
                    for row in data[1:]
                ]

            return data

        raise RuntimeError(
            "Unexpected NOAA response."
        )