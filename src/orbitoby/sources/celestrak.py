from __future__ import annotations

import json
from typing import Any

import requests

from orbitoby.sources.base import SourceAdapter


class CelesTrakSource(SourceAdapter):
    name = "celestrak"

    datasets = (
        "gp",
        "satcat",
    )

    GP_URL = (
        "https://celestrak.org/"
        "NORAD/elements/gp.php"
    )

    SATCAT_URL = (
        "https://celestrak.org/"
        "satcat/records.php"
    )

    def __init__(self) -> None:
        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent":
                    "orbitoby/0.1"
            }
        )

    def fetch(
        self,
        dataset: str,
        **params: Any,
    ) -> bytes:

        query: dict[str, str] = {
            "FORMAT": "JSON",
        }

        if params.get("norad_id") is not None:
            query["CATNR"] = str(
                params["norad_id"]
            )

        elif params.get("cospar_id"):
            query["INTDES"] = str(
                params["cospar_id"]
            )

        elif params.get("group"):
            query["GROUP"] = str(
                params["group"]
            )

        elif params.get("name"):
            query["NAME"] = str(
                params["name"]
            )

        elif params.get("special"):
            query["SPECIAL"] = str(
                params["special"]
            )

        else:
            raise ValueError(
                "Provide one of: "
                "norad_id, cospar_id, "
                "group, name, special."
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
                value = params.get(
                    python_name
                )

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
            raise ValueError(
                f"Unsupported CelesTrak dataset: "
                f"{dataset}"
            )

        response = self.session.get(
            url,
            params=query,
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
            return data

        raise RuntimeError(
            "Unexpected CelesTrak response."
        )