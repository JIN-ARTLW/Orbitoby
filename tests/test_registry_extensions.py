import pytest

from orbitoby.settings import (
    register_http_source,
)
from orbitoby.sources.registry import (
    build_sources,
)


def test_registry_loads_persistent_http_source(
    tmp_path,
):
    path = tmp_path / "settings.json"

    register_http_source(
        name="example",
        dataset="objects",
        url=("https://example.com/objects.json"),
        path=path,
    )

    sources = build_sources(settings_path=path)

    assert "example" in sources
    assert sources["example"].datasets == ("objects",)


def test_registry_rejects_builtin_name_collision(
    tmp_path,
):
    path = tmp_path / "settings.json"

    register_http_source(
        name="gcat",
        dataset="demo",
        url=("https://example.com/demo.json"),
        path=path,
    )

    with pytest.raises(
        RuntimeError,
        match="conflicts",
    ):
        build_sources(settings_path=path)
