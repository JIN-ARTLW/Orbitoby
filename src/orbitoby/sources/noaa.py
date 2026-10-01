from __future__ import annotations

import json
from typing import Any, ClassVar

from orbitoby.http import SafeHttpClient
from orbitoby.sources.base import SourceAdapter
from orbitoby.sources.metadata import source_metadata


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

    URLS: ClassVar[dict[str, str]] = {
        "solar_cycle": (
            "https://services.swpc.noaa.gov/"
            "json/solar-cycle/"
            "observed-solar-cycle-indices.json"
        ),
        "f107_cycle": (
            "https://services.swpc.noaa.gov/json/solar-cycle/f10-7cm-flux.json"
        ),
        "sunspots": ("https://services.swpc.noaa.gov/json/solar-cycle/sunspots.json"),
        "f107_recent": ("https://services.swpc.noaa.gov/json/f107_cm_flux.json"),
        "f107_30day": ("https://services.swpc.noaa.gov/products/10cm-flux-30-day.json"),
        "kp_recent": ("https://services.swpc.noaa.gov/json/planetary_k_index_1m.json"),
        "dst_recent": ("https://services.swpc.noaa.gov/products/kyoto-dst.json"),
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
            url = self.URLS[dataset]

        except KeyError as exc:
            raise ValueError(f"Unsupported NOAA dataset: {dataset}") from exc

        return self.http.get(url)

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
            # 일부 NOAA product는
            # [["header1", "header2"], [...], ...]
            # 형태로 제공됨.
            if data and isinstance(
                data[0],
                list,
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

        raise RuntimeError("Unexpected NOAA response.")
