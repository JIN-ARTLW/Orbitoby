from __future__ import annotations

from orbitoby.sources.base import SourceAdapter
from orbitoby.sources.celestrak import CelesTrakSource
from orbitoby.sources.gcat import GCATSource
from orbitoby.sources.launchlibrary import (
    LaunchLibrarySource,
)
from orbitoby.sources.noaa import NoaaSource
from orbitoby.sources.satnogs import SatNOGSSource
from orbitoby.sources.spacetrack import SpaceTrackSource


def build_sources() -> dict[str, SourceAdapter]:
    """
    Archive에서 사용할 모든 source adapter 등록.
    """

    sources: list[SourceAdapter] = [
        SpaceTrackSource(),
        CelesTrakSource(),
        NoaaSource(),
        SatNOGSSource(),
        GCATSource(),
        LaunchLibrarySource(),
    ]

    return {
        source.name: source
        for source in sources
    }