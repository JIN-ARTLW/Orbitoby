from orbitoby.sources.metadata import (
    builtin_source_metadata,
)


def test_builtin_source_metadata_matches_current_sources():
    metadata = builtin_source_metadata()

    assert {
        "celestrak",
        "gcat",
        "launchlibrary",
        "noaa",
        "satnogs",
        "spacetrack",
    } <= set(metadata)


def test_metadata_has_host_allowlist():
    for source in builtin_source_metadata().values():
        assert source.host_allowlist
        assert source.homepage.startswith("https://")


def test_unknown_policy_is_explicit():
    source = builtin_source_metadata()["gcat"]

    assert source.policy.commercial_use in {
        "allowed",
        "restricted",
        "unknown",
    }
