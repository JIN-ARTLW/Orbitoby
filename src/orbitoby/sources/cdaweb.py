from __future__ import annotations

from typing import ClassVar

from orbitoby.sources.hapi import (
    HAPISource,
)


class CDAWebSource(HAPISource):
    """NASA SPDF CDAWeb HAPI access.

    Curated aliases focus on OMNI data required by
    Orbitoby's initial science workflow. Raw CDAWeb
    HAPI dataset IDs remain usable directly.
    """

    name = "cdaweb"

    BASE_URL = "https://cdaweb.gsfc.nasa.gov/hapi"

    REQUEST_STYLE = "2"

    # Provider-specific TLS/connect allowance.
    CONNECT_TIMEOUT = 30.0

    PROFILES: ClassVar[dict[str, str]] = {
        "omni_hourly": ("OMNI2_H0_MRG1HR"),
        "omni_1min": ("OMNI_HRO2_1MIN"),
        "omni_5min": ("OMNI_HRO2_5MIN"),
    }

    datasets = tuple(PROFILES)
