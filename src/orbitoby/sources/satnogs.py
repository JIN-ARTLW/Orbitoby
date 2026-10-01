from __future__ import annotations

import json
from typing import Any, ClassVar

from orbitoby.http import SafeHttpClient
from orbitoby.sources.base import SourceAdapter
from orbitoby.sources.metadata import source_metadata


class SatNOGSSource(SourceAdapter):
    """
    SatNOGS DB adapter.

    지원:
    - satellites
    - tle
    - tle_historical
    - transmitters
    - optical_observations

    주의:
    SatNOGS의 일부 endpoint는 limit/page_size 같은
    pagination parameter를 안정적으로 지원하지 않는다.

    따라서 limit은 서버에 보내지 않고
    normalize 단계에서 로컬 slicing에 사용한다.
    """

    name = "satnogs"

    datasets = (
        "satellites",
        "tle",
        "tle_historical",
        "transmitters",
        "optical_observations",
    )

    BASE_URL = "https://db.satnogs.org/api"

    ENDPOINTS: ClassVar[dict[str, str]] = {
        "satellites": "/satellites/",
        "tle": "/tle/",
        "tle_historical": "/tle/historical/",
        "transmitters": "/transmitters/",
        "optical_observations": "/optical-observations/",
    }

    # 우리 archive 내부에서만 사용하는 parameter.
    # SatNOGS 서버에는 보내지 않는다.
    LOCAL_PARAMS: ClassVar[set[str]] = {
        "limit",
        "local_limit",
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
        """
        SatNOGS API의 raw response를 반환한다.

        limit/local_limit은 서버에 전달하지 않는다.
        """

        try:
            endpoint = self.ENDPOINTS[dataset]

        except KeyError as exc:
            raise ValueError(f"Unsupported SatNOGS dataset: {dataset}") from exc

        url = f"{self.BASE_URL}{endpoint}"

        # archive 내부용 parameter 제거
        remote_params = {
            key: value
            for key, value in params.items()
            if (value is not None and key not in self.LOCAL_PARAMS)
        }

        return self.http.get(
            url,
            params=remote_params or None,
        )

    # ------------------------------------------------------------------
    # Normalize
    # ------------------------------------------------------------------

    def normalize(
        self,
        dataset: str,
        payload: bytes,
        **context: Any,
    ) -> list[dict]:
        """
        SatNOGS response를 Python record list로 변환한다.

        limit/local_limit이 있으면 여기서 로컬 slicing한다.
        """

        data = json.loads(payload)

        if isinstance(data, dict):
            if "results" in data:
                records = data["results"]
            else:
                records = [data]

        elif isinstance(data, list):
            records = data

        else:
            raise TypeError("Unexpected SatNOGS response format.")

        limit = context.get(
            "local_limit",
            context.get("limit"),
        )

        if limit is not None:
            limit = int(limit)

            if limit < 0:
                raise ValueError("limit must be >= 0")

            records = records[:limit]

        return records
