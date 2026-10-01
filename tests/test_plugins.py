from orbitoby.sources.plugins import (
    discover_source_plugins,
    load_trusted_source_plugins,
)


def test_plugin_discovery_is_safe_without_plugins():
    result = discover_source_plugins()

    assert isinstance(
        result,
        list,
    )


def test_untrusted_plugins_are_not_loaded():
    result = load_trusted_source_plugins(set())

    assert result == {}
