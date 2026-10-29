import pytest

import orbitoby as ob


class FakeArchive:
    def __init__(self):
        self.calls = []
        self.closed = False

    def register_http_source(self, **kwargs):
        self.calls.append(("add", kwargs))
        return ["my_source"]

    def unregister_http_source(self, name, *, dataset=None):
        self.calls.append(("remove", name, dataset))
        return []

    def reload_sources(self):
        self.calls.append(("refresh",))
        return ["gfz"]

    def plugin_candidates(self):
        return [{"name": "test_plugin"}]

    def trust_source_plugin(self, name):
        self.calls.append(("trust", name))
        return ["gfz", "test_plugin"]

    def untrust_source_plugin(self, name):
        self.calls.append(("untrust", name))
        return ["gfz"]

    def reindex(self, **kwargs):
        self.calls.append(("reindex", kwargs))
        return [{"status": "ok", "artifacts": 1}]

    def close(self):
        self.closed = True


@pytest.fixture
def archive(monkeypatch):
    from orbitoby import service

    fake = FakeArchive()
    monkeypatch.setattr(service, "Archive", lambda: fake)
    return fake


def test_add_source_requires_explicit_product(archive):
    with pytest.raises(ValueError, match="dataset"):
        ob.add_source("my_source", url="https://example.org/data.json")

    assert archive.calls == []


def test_add_source_uses_core_without_fetching(archive):
    result = ob.add_source(
        "my_source",
        url="https://example.org/data.json",
        dataset="measurements",
    )

    assert len(result) == 1
    assert archive.calls[0][0] == "add"
    assert archive.calls[0][1]["dataset"] == "measurements"
    assert archive.closed


@pytest.mark.parametrize(
    "url",
    [
        "http://example.org/data",
        "https://localhost/data",
        "https://127.0.0.1/data",
        "https://example.org/data?token=SECRET",
        "https://user:pass@example.org/data",
    ],
)
def test_add_source_rejects_unsafe_url(url, archive):
    with pytest.raises(ValueError):
        ob.add_source(
            "my_source",
            url=url,
            dataset="measurements",
        )

    assert archive.calls == []


def test_remove_source_delegates_to_core(archive):
    ob.remove_source("my_source", dataset="measurements")
    assert archive.calls == [("remove", "my_source", "measurements")]


def test_refresh_sources_uses_core(archive):
    result = ob.refresh_sources()

    assert archive.calls == [("refresh",)]
    assert len(result) == 1


def test_plugin_requires_explicit_confirmation(archive):
    with pytest.raises(ValueError, match="confirm=True"):
        ob.trust_plugin("test_plugin")

    assert archive.calls == []


def test_plugin_trust_requires_discovery(archive):
    with pytest.raises(ValueError, match="not a discovered"):
        ob.trust_plugin("unknown", confirm=True)

    assert archive.calls == []


def test_plugin_trust_uses_core_after_approval(archive):
    ob.trust_plugin("test_plugin", confirm=True)
    assert archive.calls == [("trust", "test_plugin")]


def test_untrust_plugin_uses_core(archive):
    ob.untrust_plugin("test_plugin")
    assert archive.calls == [("untrust", "test_plugin")]


def test_reindex_preserves_core_options(archive):
    result = ob.rebuild_index(
        source="gfz",
        batch_size=250,
        progress=False,
    )

    assert len(result) == 1

    assert archive.calls == [
        (
            "reindex",
            {
                "source": "gfz",
                "dataset": None,
                "batch_size": 250,
                "progress": False,
            },
        )
    ]


@pytest.mark.parametrize("invalid", [0, -1, True, 1.5])
def test_invalid_batch_size_rejected(invalid, archive):
    with pytest.raises(ValueError, match="positive integer"):
        ob.rebuild_index(batch_size=invalid)

    assert archive.calls == []
