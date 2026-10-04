from __future__ import annotations

from typing import Any, ClassVar

from orbitoby.sources.hapi import (
    HAPISource,
)
from orbitoby.sources.latis import (
    LaTiSClient,
)


class LISIRDSource(HAPISource):
    """LASP LISIRD scientific time-series access.

    Metadata/catalog discovery uses HAPI where available.

    Data retrieval uses native LaTiS because the current
    LISIRD HAPI data endpoint can terminate chunked
    responses prematurely while the equivalent LaTiS
    endpoint succeeds.

    FISM2 products are native LaTiS datasets and are
    intentionally exposed through the same LASP source.
    """

    name = "lisird"

    BASE_URL = "https://lasp.colorado.edu/lisird/latis/hapi"

    LATIS_BASE_URL = "https://lasp.colorado.edu/lisird/latis"

    REQUEST_STYLE = "3"

    PROFILES: ClassVar[dict[str, str]] = {
        "eve_bands": ("sdo_eve_bands_l3"),
        "eve_lines": ("sdo_eve_lines_l3"),
        "timed_see_lines": ("timed_see_lines_l3"),
        "timed_see_xps": ("timed_see_xps_diodes_l3"),
        "mgii": ("composite_mg_index"),
        "solar_radio": ("noaa_radio_flux"),
    }

    LATIS_PROFILES: ClassVar[dict[str, str]] = {
        "fism2_daily_bands": ("fism_daily_bands"),
        "fism2_daily_spectrum": ("fism_daily_hr"),
        "fism2_flare_bands": ("fism_flare_bands"),
        "fism2_flare_spectrum": ("fism_flare_hr"),
    }

    datasets = (
        *tuple(PROFILES),
        *tuple(LATIS_PROFILES),
    )

    raw_extension = "csv"

    def __init__(
        self,
    ) -> None:
        super().__init__()

        self.latis = LaTiSClient(
            base_url=self.LATIS_BASE_URL,
            allowed_hosts=(self.metadata.host_allowlist),
            http=self.http,
        )

        # Preserve explicit ``source.latis`` replacement
        # semantics just as HAPI preserves ``source.http``.
        self._default_latis = self.latis

        self.metadata_latis = LaTiSClient(
            base_url=self.LATIS_BASE_URL,
            allowed_hosts=(self.metadata.host_allowlist),
            http=self.metadata_http,
        )

    def _metadata_latis_client(
        self,
    ):
        """Return the effective LaTiS metadata transport."""

        if self.latis is self._default_latis:
            return self.metadata_latis

        return self.latis

    def _latis_dataset_id(
        self,
        dataset: str,
    ) -> str:
        if dataset in self.LATIS_PROFILES:
            return self.LATIS_PROFILES[dataset]

        return self.remote_dataset_id(dataset)

    def info(
        self,
        dataset: str,
    ) -> dict:
        if dataset not in self.LATIS_PROFILES:
            return super().info(dataset)

        remote_id = self.LATIS_PROFILES[dataset]

        payload = self._metadata_latis_client().dds(remote_id)

        try:
            descriptor = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RuntimeError("LaTiS DDS response is not valid UTF-8.") from exc

        return {
            "dataset": remote_id,
            "transport": "latis",
            "format": "dds",
            "descriptor": descriptor,
        }

    def fetch(
        self,
        dataset: str,
        **params: Any,
    ) -> bytes:
        allowed = {
            "start",
            "end",
            "parameters",
            "limit",
        }

        unknown = set(params) - allowed

        if unknown:
            raise ValueError(
                "Unsupported LISIRD fetch parameter(s): " + ", ".join(sorted(unknown))
            )

        start = params.get("start")

        end = params.get("end")

        if start is None:
            raise ValueError("start is required for LISIRD data.")

        if end is None:
            raise ValueError("end is required for LISIRD data.")

        return self.latis.fetch_csv(
            self._latis_dataset_id(dataset),
            start=start,
            end=end,
            variables=params.get("parameters"),
            limit=params.get("limit"),
        )

    def normalize(
        self,
        dataset: str,
        payload: bytes,
        **context: Any,
    ) -> list[dict]:
        del context

        self._latis_dataset_id(dataset)

        return self.latis.normalize_csv(payload)
