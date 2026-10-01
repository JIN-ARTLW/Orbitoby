from __future__ import annotations

from typing import ClassVar

from orbitoby.sources.hapi import (
    HAPISource,
)


class WDCKyotoSource(HAPISource):
    """WDC for Geomagnetism, Kyoto HAPI access.

    Unversioned aliases use the provider's Best Available
    datasets. Their versionCode field is preserved exactly
    in normalized records.
    """

    name = "wdc_kyoto"

    BASE_URL = "https://wdc.kugi.kyoto-u.ac.jp/hapi"

    REQUEST_STYLE = "3"

    PROFILES: ClassVar[dict[str, str]] = {
        "dst_hourly": ("hour_dst"),
        "ae_hourly": ("hour_ae"),
        "ae_minute": ("min_ae"),
        "asysym_minute": ("min_asysym"),
        "kp_ap_3hour": ("hour3h_kp"),
        "ap_daily": ("day_ap"),
    }

    datasets = tuple(PROFILES)
