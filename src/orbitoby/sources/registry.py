from __future__ import annotations

from pathlib import Path

from orbitoby.settings import (
    load_settings,
)
from orbitoby.sources.base import (
    SourceAdapter,
)
from orbitoby.sources.celestrak import (
    CelesTrakSource,
)
from orbitoby.sources.declarative import (
    build_declarative_sources,
)
from orbitoby.sources.gcat import (
    GCATSource,
)
from orbitoby.sources.launchlibrary import (
    LaunchLibrarySource,
)
from orbitoby.sources.noaa import (
    NoaaSource,
)
from orbitoby.sources.plugins import (
    load_trusted_source_plugins,
)
from orbitoby.sources.satnogs import (
    SatNOGSSource,
)
from orbitoby.sources.spacetrack import (
    SpaceTrackSource,
)


def _builtin_sources() -> dict[
    str,
    SourceAdapter,
]:
    sources: list[SourceAdapter] = [
        SpaceTrackSource(),
        CelesTrakSource(),
        NoaaSource(),
        SatNOGSSource(),
        GCATSource(),
        LaunchLibrarySource(),
    ]

    return {source.name: source for source in sources}


def _merge_source(
    result: dict[
        str,
        SourceAdapter,
    ],
    source: SourceAdapter,
    *,
    kind: str,
) -> None:
    if source.name in result:
        raise RuntimeError(
            f"{kind} source "
            f"{source.name!r} conflicts "
            "with an already registered source."
        )

    result[source.name] = source


def build_sources(
    *,
    settings_path: str | Path | None = None,
) -> dict[
    str,
    SourceAdapter,
]:
    """Build the active local source registry."""

    result = _builtin_sources()

    settings = load_settings(settings_path)

    declarative = build_declarative_sources(settings["http_sources"])

    for source in declarative.values():
        _merge_source(
            result,
            source,
            kind="user-defined",
        )

    trusted_plugins = load_trusted_source_plugins(set(settings["trusted_plugins"]))

    for source in trusted_plugins.values():
        _merge_source(
            result,
            source,
            kind="plugin",
        )

    return result
