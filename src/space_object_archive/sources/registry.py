from __future__ import annotations

from space_object_archive.sources.base import SourceAdapter
from space_object_archive.sources.celestrak import CelesTrakSource
from space_object_archive.sources.gcat import GCATSource
from space_object_archive.sources.launchlibrary import (
    LaunchLibrarySource,
)
from space_object_archive.sources.noaa import NoaaSource
from space_object_archive.sources.satnogs import SatNOGSSource
from space_object_archive.sources.spacetrack import SpaceTrackSource


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