from orbitoby.settings import (
    load_settings,
    register_http_source,
    trust_plugin,
    unregister_http_source,
    untrust_plugin,
)


def test_settings_round_trip(tmp_path):
    path = tmp_path / "settings.json"

    trust_plugin(
        "demo-plugin",
        path=path,
    )

    settings = load_settings(path)

    assert settings["trusted_plugins"] == ["demo-plugin"]

    untrust_plugin(
        "demo-plugin",
        path=path,
    )

    assert load_settings(path)["trusted_plugins"] == []


def test_http_source_persistence(tmp_path):
    path = tmp_path / "settings.json"

    register_http_source(
        name="demo",
        dataset="objects",
        url="https://example.com/objects.json",
        path=path,
    )

    settings = load_settings(path)

    assert len(settings["http_sources"]) == 1
    assert settings["http_sources"][0]["name"] == "demo"

    unregister_http_source(
        "demo",
        path=path,
    )

    assert load_settings(path)["http_sources"] == []


def test_http_source_registration_replaces_same_dataset(
    tmp_path,
):
    path = tmp_path / "settings.json"

    register_http_source(
        name="demo",
        dataset="objects",
        url="https://example.com/a.json",
        path=path,
    )

    register_http_source(
        name="demo",
        dataset="objects",
        url="https://example.com/b.json",
        path=path,
    )

    items = load_settings(path)["http_sources"]

    assert len(items) == 1
    assert items[0]["url"].endswith("b.json")
