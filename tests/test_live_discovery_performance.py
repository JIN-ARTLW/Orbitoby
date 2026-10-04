from __future__ import annotations

from collections import Counter
from threading import Barrier

import requests

from orbitoby.source_api import SourceAPI


class DummyAdapter:
    def __init__(
        self,
        *datasets,
    ):
        self.datasets = datasets


class DummyArchive(SourceAPI):
    def __init__(
        self,
        sources,
        behavior=None,
    ):
        self.sources = sources
        self.behavior = behavior if behavior is not None else {}
        self.calls = Counter()

    def get_source(
        self,
        name,
    ):
        try:
            return self.sources[name]
        except KeyError as exc:
            raise ValueError(f"Unknown source: {name}") from exc

    def _dataset_row(
        self,
        source_name,
        dataset,
        *,
        live=False,
    ):
        if live:
            self.calls[
                (
                    source_name,
                    dataset,
                )
            ] += 1

            action = self.behavior.get(
                (
                    source_name,
                    dataset,
                )
            )

            if callable(action):
                action()

            elif isinstance(
                action,
                BaseException,
            ):
                raise action

        metric = "wanted" if dataset == "wanted" else "other"

        return {
            "source": source_name,
            "dataset": dataset,
            "canonical_metrics": [
                metric,
            ],
            "categories": [
                "test",
            ],
            "data_scope": "global",
            "object_scope": "none",
            "available_start": ("2020-01-01" if live else None),
            "available_end": ("2020-01-02" if live else None),
            "availability_source": ("provider" if live else "unknown"),
            "availability_error": None,
        }


def test_live_discovery_filters_before_network():
    archive = DummyArchive(
        {
            "source": DummyAdapter(
                "wanted",
                "discarded",
            )
        }
    )

    rows = archive.datasets(
        metric="wanted",
        live=True,
    )

    assert [row["dataset"] for row in rows] == ["wanted"]

    assert archive.calls == Counter(
        {
            (
                "source",
                "wanted",
            ): 1
        }
    )


def test_live_discovery_success_is_cached():
    archive = DummyArchive(
        {
            "source": DummyAdapter(
                "wanted",
            )
        }
    )

    first = archive.datasets(live=True)

    second = archive.datasets(live=True)

    assert first == second

    assert (
        archive.calls[
            (
                "source",
                "wanted",
            )
        ]
        == 1
    )


def test_connection_failure_opens_source_circuit():
    archive = DummyArchive(
        {
            "bad": DummyAdapter(
                "a",
                "b",
                "c",
            )
        },
        behavior={
            (
                "bad",
                "a",
            ): requests.ConnectionError("provider unavailable")
        },
    )

    rows = archive.datasets(live=True)

    assert (
        archive.calls[
            (
                "bad",
                "a",
            )
        ]
        == 1
    )

    assert (
        archive.calls[
            (
                "bad",
                "b",
            )
        ]
        == 0
    )

    assert (
        archive.calls[
            (
                "bad",
                "c",
            )
        ]
        == 0
    )

    assert rows[0]["availability_error"].startswith("ConnectionError:")

    assert rows[1]["availability_error"].startswith("CircuitOpen:")

    assert rows[2]["availability_error"].startswith("CircuitOpen:")


def test_dataset_specific_value_error_does_not_open_circuit():
    archive = DummyArchive(
        {
            "source": DummyAdapter(
                "a",
                "b",
            )
        },
        behavior={
            (
                "source",
                "a",
            ): ValueError("dataset metadata invalid")
        },
    )

    rows = archive.datasets(live=True)

    assert len(rows) == 2

    assert (
        archive.calls[
            (
                "source",
                "a",
            )
        ]
        == 1
    )

    assert (
        archive.calls[
            (
                "source",
                "b",
            )
        ]
        == 1
    )


def test_independent_sources_run_concurrently():
    barrier = Barrier(2)

    def rendezvous():
        barrier.wait(timeout=2.0)

    archive = DummyArchive(
        {
            "one": DummyAdapter(
                "a",
            ),
            "two": DummyAdapter(
                "a",
            ),
        },
        behavior={
            (
                "one",
                "a",
            ): rendezvous,
            (
                "two",
                "a",
            ): rendezvous,
        },
    )

    rows = archive.datasets(live=True)

    assert len(rows) == 2

    assert (
        archive.calls[
            (
                "one",
                "a",
            )
        ]
        == 1
    )

    assert (
        archive.calls[
            (
                "two",
                "a",
            )
        ]
        == 1
    )


def test_http_error_does_not_open_provider_circuit():
    archive = DummyArchive(
        {
            "source": DummyAdapter(
                "a",
                "b",
            )
        },
        behavior={
            (
                "source",
                "a",
            ): requests.HTTPError("400 Client Error")
        },
    )

    rows = archive.datasets(live=True)

    assert len(rows) == 2

    assert (
        archive.calls[
            (
                "source",
                "a",
            )
        ]
        == 1
    )

    # HTTP 4xx may be dataset-specific.
    # It must not suppress another dataset.
    assert (
        archive.calls[
            (
                "source",
                "b",
            )
        ]
        == 1
    )

    assert rows[0]["availability_error"].startswith("HTTPError:")

    assert rows[1]["availability_error"] is None
