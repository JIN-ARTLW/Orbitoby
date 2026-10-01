from __future__ import annotations

from dataclasses import asdict

from orbitoby.settings import (
    register_http_source,
    trust_plugin,
    unregister_http_source,
    untrust_plugin,
)
from orbitoby.sources.metadata import (
    builtin_source_metadata,
)
from orbitoby.sources.plugins import (
    discover_source_plugins,
)
from orbitoby.sources.registry import (
    build_sources,
)


class SourceAPI:
    """Source discovery, policy and local-extension APIs."""

    def reload_sources(
        self,
    ) -> list[str]:
        self.sources = build_sources(
            credentials=getattr(
                self,
                "credentials",
                None,
            )
        )

        return sorted(self.sources)

    def source_info(
        self,
        name: str | None = None,
    ):
        builtin = builtin_source_metadata()

        def info(
            source_name,
        ):
            adapter = self.get_source(source_name)

            metadata = getattr(
                adapter,
                "metadata",
                None,
            )

            if metadata is None:
                metadata = builtin.get(source_name)

            result = {}

            if metadata is not None:
                result.update(asdict(metadata))

            result["name"] = source_name
            result["datasets"] = list(adapter.datasets)

            return result

        if name is not None:
            return info(name)

        return [info(source_name) for source_name in sorted(self.sources)]

    def credits(
        self,
    ) -> list[dict]:
        result = []

        for source in self.source_info():
            result.append(
                {
                    "name": source["name"],
                    "title": source.get(
                        "title",
                        source["name"],
                    ),
                    "homepage": (source.get("homepage")),
                }
            )

        return result

    def licenses(
        self,
    ) -> list[dict]:
        result = []

        for source in self.source_info():
            policy = source.get("policy")

            result.append(
                {
                    "name": source["name"],
                    "policy": policy,
                }
            )

        return result

    def plugin_candidates(
        self,
    ) -> list[dict]:
        return [asdict(candidate) for candidate in discover_source_plugins()]

    def trust_source_plugin(
        self,
        name: str,
    ) -> list[str]:
        trust_plugin(name)

        return self.reload_sources()

    def untrust_source_plugin(
        self,
        name: str,
    ) -> list[str]:
        untrust_plugin(name)

        return self.reload_sources()

    def register_http_source(
        self,
        *,
        name: str,
        dataset: str,
        url: str,
        format: str = "json",
        root_key: str | None = None,
        homepage: str | None = None,
        description_en: str = "",
        description_ko: str = "",
    ) -> list[str]:
        register_http_source(
            name=name,
            dataset=dataset,
            url=url,
            format=format,
            root_key=root_key,
            homepage=homepage,
            description_en=(description_en),
            description_ko=(description_ko),
        )

        return self.reload_sources()

    def unregister_http_source(
        self,
        name: str,
        *,
        dataset: str | None = None,
    ) -> list[str]:
        unregister_http_source(
            name,
            dataset=dataset,
        )

        return self.reload_sources()
