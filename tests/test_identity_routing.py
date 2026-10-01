from orbitoby.sources.cdaweb import (
    CDAWebSource,
)
from orbitoby.sources.celestrak import (
    CelesTrakSource,
)
from orbitoby.sources.gcat import (
    GCATSource,
)
from orbitoby.sources.launchlibrary import (
    LaunchLibrarySource,
)
from orbitoby.sources.lisird import (
    LISIRDSource,
)
from orbitoby.sources.noaa import (
    NoaaSource,
)
from orbitoby.sources.satnogs import (
    SatNOGSSource,
)
from orbitoby.sources.spacetrack import (
    SpaceTrackSource,
)
from orbitoby.sources.wdc_kyoto import (
    WDCKyotoSource,
)


def test_science_series_skip_identity_store():
    assert not CDAWebSource().should_index_identity("omni_hourly")

    assert not LISIRDSource().should_index_identity("fism2_daily_bands")

    assert not WDCKyotoSource().should_index_identity("dst_hourly")

    assert not NoaaSource().should_index_identity("f107_recent")


def test_object_sources_opt_into_identity_store():
    assert CelesTrakSource().should_index_identity("gp")

    assert GCATSource().should_index_identity("satcat")

    assert SatNOGSSource().should_index_identity("satellites")

    assert LaunchLibrarySource().should_index_identity("payloads")


def test_launchlibrary_non_object_datasets_skip_identity():
    source = LaunchLibrarySource()

    assert not source.should_index_identity("launches")

    assert not source.should_index_identity("agencies")


def test_spacetrack_gp_history_indexes_identity():
    source = SpaceTrackSource()

    assert source.should_index_identity("gp_history")
