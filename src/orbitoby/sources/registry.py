from __future__ import annotations

from pathlib import Path

from orbitoby.auth import (
    CredentialManager,
    default_credential_manager,
)
from orbitoby.settings import (
    load_settings,
)
from orbitoby.sources.base import (
    SourceAdapter,
)
from orbitoby.sources.cdaweb import (
    CDAWebSource,
)
from orbitoby.sources.celestrak import (
    CelesTrakSource,
)
from orbitoby.sources.declarative import (
    build_declarative_sources,
)
from orbitoby.sources.discos import DiscosSource
from orbitoby.sources.donki import DONKISource
from orbitoby.sources.gcat import (
    GCATSource,
)
from orbitoby.sources.gfz import GFZSource
from orbitoby.sources.launchlibrary import (
    LaunchLibrarySource,
)
from orbitoby.sources.lisird import (
    LISIRDSource,
)
from orbitoby.sources.noaa import (
    NoaaSource,
)
from orbitoby.sources.nrcan import NRCanSource
from orbitoby.sources.plugins import (
    load_trusted_source_plugins,
)
from orbitoby.sources.satnogs import (
    SatNOGSSource,
)
from orbitoby.sources.silso import SILSOSource
from orbitoby.sources.spacetrack import (
    SpaceTrackSource,
)
from orbitoby.sources.swarm import SwarmSource
from orbitoby.sources.wdc_kyoto import (
    WDCKyotoSource,
)


def _builtin_sources(
    credentials: CredentialManager,
) -> dict[
    str,
    SourceAdapter,
]:
    sources: list[SourceAdapter] = [
        SpaceTrackSource(credentials=credentials),
        CelesTrakSource(),
        NoaaSource(),
        DONKISource(),
        NRCanSource(),
        GFZSource(),
        SILSOSource(),
        SatNOGSSource(),
        GCATSource(),
        LaunchLibrarySource(),
        CDAWebSource(),
        LISIRDSource(),
        WDCKyotoSource(),
        SwarmSource(),
        DiscosSource(credentials=credentials),
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
            "with an already registered "
            "source."
        )

    result[source.name] = source


def build_sources(
    *,
    settings_path: (str | Path | None) = None,
    credentials: (CredentialManager | None) = None,
) -> dict[
    str,
    SourceAdapter,
]:
    """Build the active local source registry."""

    manager = credentials or default_credential_manager()

    result = _builtin_sources(manager)

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
