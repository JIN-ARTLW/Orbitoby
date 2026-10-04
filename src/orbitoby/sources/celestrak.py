from __future__ import annotations

import csv
import io
import json
from typing import Any

from orbitoby.http import SafeHttpClient
from orbitoby.sources.base import SourceAdapter
from orbitoby.sources.metadata import source_metadata


class CelesTrakSource(SourceAdapter):
    name = "celestrak"
    identity_datasets = frozenset(
        {
            "gp",
            "satcat",
        }
    )

    datasets = (
        "gp",
        "satcat",
    )

    GP_URL = "https://celestrak.org/NORAD/elements/gp.php"

    SATCAT_URL = "https://celestrak.org/satcat/records.php"

    SATCAT_BULK_URL = "https://celestrak.org/pub/satcat.csv"

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

    def should_index_identity_request(
        self,
        dataset: str,
        **params: Any,
    ) -> bool:
        if dataset == "satcat" and params.get("all") is True:
            return False

        return self.should_index_identity(dataset)

    def raw_extension_for(
        self,
        dataset: str,
        **params: Any,
    ) -> str:
        if dataset == "satcat" and params.get("all") is True:
            return "csv"

        return self.raw_extension

    def fetch(
        self,
        dataset: str,
        **params: Any,
    ) -> bytes:

        if dataset == "satcat" and params.get("all") is True:
            unknown = set(params) - {"all"}

            if unknown:
                raise ValueError("Bulk CelesTrak SATCAT accepts only all=True.")

            return self.http.get(self.SATCAT_BULK_URL)

        query: dict[str, str] = {
            "FORMAT": "JSON",
        }

        if params.get("norad_id") is not None:
            query["CATNR"] = str(params["norad_id"])

        elif params.get("cospar_id"):
            query["INTDES"] = str(params["cospar_id"])

        elif params.get("group"):
            query["GROUP"] = str(params["group"])

        elif params.get("name"):
            query["NAME"] = str(params["name"])

        elif params.get("special"):
            query["SPECIAL"] = str(params["special"])

        else:
            raise ValueError(
                "Provide one of: norad_id, cospar_id, group, name, special."
            )

        if dataset == "gp":
            url = self.GP_URL

        elif dataset == "satcat":
            url = self.SATCAT_URL

            optional = {
                "payloads": "PAYLOADS",
                "onorbit": "ONORBIT",
                "active": "ACTIVE",
                "max_results": "MAX",
            }

            for python_name, api_name in optional.items():
                value = params.get(python_name)

                if value is not None:
                    query[api_name] = str(
                        int(value)
                        if isinstance(
                            value,
                            bool,
                        )
                        else value
                    )

        else:
            raise ValueError(f"Unsupported CelesTrak dataset: {dataset}")

        return self.http.get(
            url,
            params=query,
        )

    def normalize(
        self,
        dataset: str,
        payload: bytes,
        **context: Any,
    ) -> list[dict]:

        if dataset == "satcat" and context.get("all") is True:
            decoded = payload.decode("utf-8-sig")

            reader = csv.DictReader(io.StringIO(decoded))

            return [dict(row) for row in reader]

        data = json.loads(payload)

        if isinstance(data, dict):
            return [data]

        if isinstance(data, list):
            return data

        raise RuntimeError("Unexpected CelesTrak response.")
