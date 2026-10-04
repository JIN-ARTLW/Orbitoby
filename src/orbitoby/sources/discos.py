from __future__ import annotations

import json
from typing import Any

from orbitoby.auth import (
    CredentialManager,
    default_credential_manager,
)
from orbitoby.http import SafeHttpClient
from orbitoby.sources.base import SourceAdapter
from orbitoby.sources.metadata import source_metadata


class DiscosSource(SourceAdapter):
    """ESA DISCOS space-object physical metadata.

    Authentication uses the user's own DISCOS API token.

    Provider-native object attributes are preserved here.
    Canonical identity and physical-property mapping belongs
    to Orbitoby's canonical research layer.
    """

    name = "discos"

    BASE_URL = "https://discosweb.esoc.esa.int/api"

    API_VERSION = "2"

    datasets = ("objects",)

    def __init__(
        self,
        *,
        credentials: CredentialManager | None = None,
        http: SafeHttpClient | None = None,
    ) -> None:
        self.metadata = source_metadata(self.name)

        self.credentials = credentials or default_credential_manager()

        self.http = http or SafeHttpClient(
            allowed_hosts=(self.metadata.host_allowlist),
            read_timeout=120.0,
        )

    def _token(
        self,
    ) -> str:
        token = self.credentials.get(
            "discos",
            "token",
            env_name="ORBITOBY_DISCOS_TOKEN",
            required=True,
        )

        assert token is not None

        token = token.strip()

        if not token:
            raise RuntimeError("DISCOS token is empty.")

        return token

    def _headers(
        self,
    ) -> dict[str, str]:
        return {
            "Authorization": (f"Bearer {self._token()}"),
            "DiscosWeb-Api-Version": (self.API_VERSION),
            "Accept": "application/json",
        }

    @staticmethod
    def _positive_identifier(
        value: object,
        *,
        name: str,
    ) -> int:
        if isinstance(
            value,
            bool,
        ):
            raise TypeError(f"{name} must be an integer identifier")

        try:
            result = int(value)
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise TypeError(f"{name} must be an integer identifier") from exc

        if result <= 0:
            raise ValueError(f"{name} must be positive")

        return result

    def fetch(
        self,
        dataset: str,
        **params: Any,
    ) -> bytes:
        if dataset != "objects":
            raise ValueError(f"Unsupported DISCOS dataset: {dataset!r}")

        allowed = {
            "norad_id",
            "discos_id",
        }

        unknown = set(params) - allowed

        if unknown:
            raise ValueError(
                "Unsupported DISCOS fetch parameter(s): " + ", ".join(sorted(unknown))
            )

        norad_id = params.get("norad_id")
        discos_id = params.get("discos_id")

        if norad_id is None and discos_id is None:
            raise ValueError("Exactly one of norad_id or discos_id is required.")

        if norad_id is not None and discos_id is not None:
            raise ValueError("norad_id and discos_id are mutually exclusive.")

        if discos_id is not None:
            object_id = self._positive_identifier(
                discos_id,
                name="discos_id",
            )

            return self.http.get(
                (f"{self.BASE_URL}/objects/{object_id}"),
                headers=self._headers(),
            )

        satno = self._positive_identifier(
            norad_id,
            name="norad_id",
        )

        return self.http.get(
            f"{self.BASE_URL}/objects",
            headers=self._headers(),
            params={
                "filter": (f"eq(satno,{satno})"),
                "page[size]": "1",
            },
        )

    def normalize(
        self,
        dataset: str,
        payload: bytes,
        **context: Any,
    ) -> list[dict]:
        del context

        if dataset != "objects":
            raise ValueError(f"Unsupported DISCOS dataset: {dataset!r}")

        try:
            document = json.loads(payload)
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise RuntimeError("ESA DISCOS returned invalid JSON.") from exc

        if not isinstance(
            document,
            dict,
        ):
            raise TypeError("DISCOS response must be a JSON object.")

        errors = document.get("errors")

        if errors:
            raise RuntimeError("ESA DISCOS returned an API error document.")

        if "data" not in document:
            raise TypeError("DISCOS response has no data member.")

        data = document["data"]

        if data is None:
            return []

        if isinstance(
            data,
            dict,
        ):
            items = [data]

        elif isinstance(
            data,
            list,
        ):
            items = data

        else:
            raise TypeError("DISCOS data must be an object, list, or null.")

        records: list[dict] = []

        for item in items:
            if not isinstance(
                item,
                dict,
            ):
                raise TypeError("DISCOS data entries must be objects.")

            attributes = item.get("attributes")

            if not isinstance(
                attributes,
                dict,
            ):
                raise TypeError("DISCOS object has no valid attributes object.")

            record = dict(attributes)

            provider_id = item.get("id")

            if provider_id is not None:
                record["discos_id"] = provider_id

            provider_type = item.get("type")

            if provider_type is not None:
                record["provider_type"] = provider_type

            relationships = item.get("relationships")

            if relationships is not None:
                record["provider_relationships"] = relationships

            links = item.get("links")

            if links is not None:
                record["provider_links"] = links

            records.append(record)

        return records
