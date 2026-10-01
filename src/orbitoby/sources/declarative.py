from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from urllib.parse import urlparse

from orbitoby.http import SafeHttpClient
from orbitoby.sources.base import SourceAdapter
from orbitoby.sources.metadata import (
    DatasetDescriptor,
    SourceMetadata,
)


@dataclass(frozen=True, slots=True)
class DeclarativeDataset:
    name: str
    url: str
    format: str
    root_key: str | None = None


class DeclarativeHTTPSource(SourceAdapter):
    """Low-code HTTPS source defined by local Orbitoby settings."""

    def __init__(
        self,
        *,
        name: str,
        definitions: list[dict],
    ) -> None:
        self.name = name

        self._definitions = {
            item["dataset"]: DeclarativeDataset(
                name=item["dataset"],
                url=item["url"],
                format=item.get(
                    "format",
                    "json",
                ),
                root_key=item.get("root_key"),
            )
            for item in definitions
        }

        self.datasets = tuple(sorted(self._definitions))

        hosts = {urlparse(item.url).hostname for item in self._definitions.values()}

        if None in hosts:
            raise ValueError("Invalid declarative source URL.")

        allowed_hosts = {host for host in hosts if host is not None}

        self.http = SafeHttpClient(allowed_hosts=allowed_hosts)

        first = definitions[0]

        self.metadata = SourceMetadata(
            name=name,
            title=name,
            homepage=first.get("homepage") or first["url"],
            auth="none",
            status="experimental",
            categories=(),
            host_allowlist=tuple(sorted(allowed_hosts)),
            description_en=first.get(
                "description_en",
                "",
            ),
            description_ko=first.get(
                "description_ko",
                "",
            ),
            datasets=tuple(
                DatasetDescriptor(
                    name=dataset,
                )
                for dataset in self.datasets
            ),
        )

    def _definition(
        self,
        dataset: str,
    ) -> DeclarativeDataset:
        try:
            return self._definitions[dataset]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported dataset {dataset!r} for source {self.name!r}"
            ) from exc

    def fetch(
        self,
        dataset: str,
        **params,
    ) -> bytes:
        definition = self._definition(dataset)

        return self.http.get(
            definition.url,
            params=(params or None),
        )

    @staticmethod
    def _json_root(
        value,
        root_key: str | None,
    ):
        if root_key is None:
            return value

        current = value

        for component in (part for part in root_key.split(".") if part):
            if not isinstance(
                current,
                dict,
            ):
                raise TypeError("root_key traversed a non-object JSON value.")

            if component not in current:
                raise ValueError(f"root_key component not found: {component!r}")

            current = current[component]

        return current

    def normalize(
        self,
        dataset: str,
        payload: bytes,
        **context,
    ) -> list[dict]:
        del context

        definition = self._definition(dataset)

        if definition.format == "json":
            value = json.loads(payload)

            value = self._json_root(
                value,
                definition.root_key,
            )

            if isinstance(
                value,
                list,
            ):
                if not all(
                    isinstance(
                        item,
                        dict,
                    )
                    for item in value
                ):
                    raise TypeError("JSON record arrays must contain objects.")

                return value

            if isinstance(
                value,
                dict,
            ):
                return [value]

            raise TypeError("JSON root must resolve to an object or array of objects.")

        text = payload.decode("utf-8-sig")

        delimiter = "," if definition.format == "csv" else "\t"

        reader = csv.DictReader(
            io.StringIO(text),
            delimiter=delimiter,
        )

        return [
            {
                str(key).strip(): (
                    value.strip()
                    if isinstance(
                        value,
                        str,
                    )
                    else value
                )
                for key, value in row.items()
                if key is not None
            }
            for row in reader
        ]


def build_declarative_sources(
    definitions: list[dict],
) -> dict[
    str,
    DeclarativeHTTPSource,
]:
    grouped: dict[
        str,
        list[dict],
    ] = {}

    for definition in definitions:
        name = definition["name"]

        grouped.setdefault(
            name,
            [],
        ).append(definition)

    return {
        name: DeclarativeHTTPSource(
            name=name,
            definitions=items,
        )
        for name, items in grouped.items()
    }
