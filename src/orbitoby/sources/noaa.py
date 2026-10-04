from __future__ import annotations

import json
from typing import Any, ClassVar

from orbitoby.http import SafeHttpClient
from orbitoby.sources.base import SourceAdapter
from orbitoby.sources.metadata import source_metadata


class NoaaSource(SourceAdapter):
    """NOAA SWPC solar and geospace products.

    Historical/cycle products and rolling operational products are
    exposed separately. Rolling GOES/RTSW products should not be
    interpreted as long-term archival datasets.
    """

    name = "noaa"

    datasets = (
        "solar_cycle",
        "f107_cycle",
        "sunspots",
        "f107_recent",
        "f107_30day",
        "kp_recent",
        "dst_recent",
        "goes_xray_1day",
        "goes_xray_7day",
        "goes_xray_flares_7day",
        "goes_integral_protons_1day",
        "goes_euvs_1day",
        "goes_magnetometers_1day",
        "rtsw_mag_1m",
        "rtsw_wind_1m",
        "alerts",
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
        "goes_xray_1day": (
            "https://services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json"
        ),
        "goes_xray_7day": (
            "https://services.swpc.noaa.gov/json/goes/primary/xrays-7-day.json"
        ),
        "goes_xray_flares_7day": (
            "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-7-day.json"
        ),
        "goes_integral_protons_1day": (
            "https://services.swpc.noaa.gov/"
            "json/goes/primary/"
            "integral-protons-1-day.json"
        ),
        "goes_euvs_1day": (
            "https://services.swpc.noaa.gov/json/goes/primary/euvs-1-day.json"
        ),
        "goes_magnetometers_1day": (
            "https://services.swpc.noaa.gov/json/goes/primary/magnetometers-1-day.json"
        ),
        "rtsw_mag_1m": ("https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json"),
        "rtsw_wind_1m": ("https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json"),
        "alerts": ("https://services.swpc.noaa.gov/products/alerts.json"),
    }

    def __init__(
        self,
        *,
        http: SafeHttpClient | None = None,
    ) -> None:
        self.metadata = source_metadata(self.name)

        self.http = http or SafeHttpClient(
            allowed_hosts=(self.metadata.host_allowlist),
            read_timeout=120.0,
        )

    def fetch(
        self,
        dataset: str,
        **params: Any,
    ) -> bytes:
        if params:
            raise ValueError(
                "NOAA SWPC built-in products do not "
                "accept Orbitoby fetch parameters. "
                "Rolling products expose the provider's "
                "current fixed window."
            )

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
        del context

        if dataset not in self.URLS:
            raise ValueError(f"Unsupported NOAA dataset: {dataset}")

        try:
            data = json.loads(payload)
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise RuntimeError("NOAA SWPC returned invalid JSON.") from exc

        if isinstance(
            data,
            dict,
        ):
            return [data]

        if isinstance(
            data,
            list,
        ):
            # Some SWPC products use:
            # [["header1", ...], ["row1", ...], ...]
            if data and isinstance(
                data[0],
                list,
            ):
                headers = data[0]

                if not all(
                    isinstance(
                        header,
                        str,
                    )
                    for header in headers
                ):
                    raise TypeError("NOAA table-style JSON has non-string headers.")

                records = []

                for row in data[1:]:
                    if not isinstance(
                        row,
                        list,
                    ):
                        raise TypeError("NOAA table-style JSON has a non-array record.")

                    if len(row) != len(headers):
                        raise ValueError(
                            "NOAA table-style JSON row does not match its header."
                        )

                    records.append(
                        dict(
                            zip(
                                headers,
                                row,
                                strict=True,
                            )
                        )
                    )

                return records

            if not all(
                isinstance(
                    row,
                    dict,
                )
                for row in data
            ):
                raise TypeError("NOAA JSON list must contain objects or table rows.")

            return [dict(row) for row in data]

        raise TypeError("Unexpected NOAA response type.")
