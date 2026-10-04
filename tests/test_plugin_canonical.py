import json

import pytest

from orbitoby.canonical import (
    MetricBinding,
    adapter_metric_bindings,
)
from orbitoby.research import ResearchAPI
from orbitoby.source_api import SourceAPI
from orbitoby.sources.base import SourceAdapter


class DemoCanonicalSource(SourceAdapter):
    name = "demo_plugin"
    datasets = ("demo_series",)

    canonical_bindings = (
        MetricBinding(
            metric="demo_metric",
            source="demo_plugin",
            dataset="demo_series",
            source_field="value",
            time_field="timestamp",
            unit="demo_unit",
        ),
    )

    def fetch(
        self,
        dataset,
        **params,
    ):
        return json.dumps(
            [
                {
                    "timestamp": ("2026-01-01T00:00:00Z"),
                    "value": 1.0,
                }
            ]
        ).encode()

    def normalize(
        self,
        dataset,
        payload,
        **context,
    ):
        return json.loads(payload)


class DemoArchive(
    SourceAPI,
    ResearchAPI,
):
    def __init__(self):
        self.sources = {
            "demo_plugin": (DemoCanonicalSource()),
        }

    def get_source(
        self,
        name,
    ):
        return self.sources[name]


def test_adapter_binding_validation():
    source = DemoCanonicalSource()

    bindings = adapter_metric_bindings(source)

    assert len(bindings) == 1
    assert bindings[0].metric == "demo_metric"


def test_dataset_info_exposes_plugin_metric():
    archive = DemoArchive()

    info = archive.dataset_info(
        "demo_plugin",
        "demo_series",
    )

    assert info["canonical_metrics"] == ["demo_metric"]

    assert info["units"] == ["demo_unit"]


def test_research_api_selects_plugin_binding():
    archive = DemoArchive()

    selected = archive._select_bindings(
        "demo_metric",
        source="demo_plugin",
        source_preference=None,
        dataset="demo_series",
    )

    assert len(selected) == 1

    assert selected[0].source == "demo_plugin"


def test_invalid_plugin_binding_source_fails_loudly():
    class BadSource(DemoCanonicalSource):
        name = "bad_plugin"

    with pytest.raises(
        ValueError,
        match="does not match adapter",
    ):
        adapter_metric_bindings(BadSource())


def test_invalid_plugin_binding_dataset_fails_loudly():
    class BadDatasetSource(DemoCanonicalSource):
        datasets = ("different",)

    with pytest.raises(
        ValueError,
        match="is not exposed",
    ):
        adapter_metric_bindings(BadDatasetSource())
