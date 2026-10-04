from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from threading import RLock
from time import monotonic

import requests

from orbitoby.canonical import (
    METRIC_BINDINGS,
    adapter_metric_bindings,
)
from orbitoby.settings import (
    register_http_source,
    trust_plugin,
    unregister_http_source,
    untrust_plugin,
)
from orbitoby.sources.metadata import (
    builtin_source_metadata,
)
from orbitoby.sources.plugins import (
    discover_source_plugins,
)
from orbitoby.sources.registry import (
    build_sources,
)

_LIVE_DISCOVERY_SUCCESS_TTL = 300.0
_LIVE_DISCOVERY_ERROR_TTL = 30.0
_LIVE_DISCOVERY_MAX_WORKERS = 8


class SourceAPI:
    """Source discovery, policy and local-extension APIs."""

    def reload_sources(
        self,
    ) -> list[str]:
        self.sources = build_sources(
            credentials=getattr(
                self,
                "credentials",
                None,
            )
        )

        return sorted(self.sources)

    def _source_context(
        self,
        source_name: str,
    ):
        adapter = self.get_source(source_name)

        metadata = getattr(
            adapter,
            "metadata",
            None,
        )

        if metadata is None:
            metadata = builtin_source_metadata().get(source_name)

        return adapter, metadata

    @staticmethod
    def _dataset_descriptor(
        metadata,
        dataset: str,
    ):
        if metadata is None:
            return None

        for descriptor in getattr(
            metadata,
            "datasets",
            (),
        ):
            if descriptor.name == dataset:
                return descriptor

        return None

    def _canonical_bindings(
        self,
        source: str,
        dataset: str,
    ):
        adapter = self.get_source(source)

        bindings = (
            *METRIC_BINDINGS,
            *adapter_metric_bindings(adapter),
        )

        return tuple(
            binding
            for binding in bindings
            if binding.source == source and binding.dataset == dataset
        )

    @staticmethod
    def _provider_time_bounds(
        provider_info: dict,
    ) -> tuple[
        object | None,
        object | None,
    ]:
        start = None
        end = None

        for key in (
            "startDate",
            "start",
            "time.min",
        ):
            if provider_info.get(key) is not None:
                start = provider_info[key]
                break

        for key in (
            "stopDate",
            "stop",
            "time.max",
        ):
            if provider_info.get(key) is not None:
                end = provider_info[key]
                break

        return start, end

    def _dataset_row(
        self,
        source_name: str,
        dataset: str,
        *,
        live: bool = False,
    ) -> dict:
        adapter, metadata = self._source_context(source_name)

        if dataset not in adapter.datasets:
            available = ", ".join(adapter.datasets)

            raise ValueError(
                f"Unknown dataset {dataset!r} "
                f"for source {source_name!r}. "
                f"Available datasets: {available}"
            )

        descriptor = self._dataset_descriptor(
            metadata,
            dataset,
        )

        bindings = self._canonical_bindings(
            source_name,
            dataset,
        )

        object_map = getattr(
            adapter,
            "dataset_objects",
            {},
        )

        objects = tuple(
            object_map.get(
                dataset,
                (),
            )
        )

        if objects:
            object_scope = "fixed"

        elif adapter.should_index_identity(dataset):
            object_scope = "catalogue"

        else:
            object_scope = "none"

        cadence_map = getattr(
            adapter,
            "dataset_cadence",
            {},
        )

        cadence = cadence_map.get(dataset)

        coverage_map = getattr(
            adapter,
            "dataset_coverage",
            {},
        )

        coverage = coverage_map.get(dataset)

        available_start = None
        available_end = None
        availability_source = "unknown"

        if isinstance(
            coverage,
            dict,
        ):
            available_start = coverage.get("start")
            available_end = coverage.get("end")
            availability_source = coverage.get(
                "source",
                "static",
            )

        elif (
            isinstance(
                coverage,
                (tuple, list),
            )
            and len(coverage) == 2
        ):
            available_start = coverage[0]
            available_end = coverage[1]
            availability_source = "static"

        live_info = getattr(
            adapter,
            "info",
            None,
        )

        live_supported = callable(live_info)

        if live:
            if not live_supported:
                raise ValueError(
                    f"Source {source_name!r} does not expose provider dataset metadata."
                )

            provider_info = live_info(dataset)

            if not isinstance(
                provider_info,
                dict,
            ):
                raise TypeError("Provider dataset metadata must be a dictionary.")

            (
                provider_start,
                provider_end,
            ) = self._provider_time_bounds(provider_info)

            if provider_start is not None:
                available_start = provider_start

            if provider_end is not None:
                available_end = provider_end

            availability_source = "provider"

        canonical_metrics = sorted({binding.metric for binding in bindings})

        units = sorted(
            {binding.unit for binding in bindings if binding.unit is not None}
        )

        artifact_kinds = sorted(
            {
                binding.artifact_kind
                for binding in bindings
                if binding.artifact_kind is not None
            }
        )

        methods = sorted(
            {binding.method for binding in bindings if binding.method is not None}
        )

        source_categories = tuple(
            getattr(
                metadata,
                "categories",
                (),
            )
        )

        dataset_categories = tuple(
            getattr(
                descriptor,
                "categories",
                (),
            )
        )

        categories = dataset_categories if dataset_categories else source_categories

        if object_scope == "fixed":
            data_scope = "fixed_object"

        elif object_scope == "catalogue":
            data_scope = "object_catalogue"

        elif "space_weather_events" in categories or "launch" in categories:
            data_scope = "event"

        elif "mission" in categories:
            data_scope = "mission"

        else:
            data_scope = "global"

        source_auth = getattr(
            metadata,
            "auth",
            "unknown",
        )

        descriptor_auth = bool(
            getattr(
                descriptor,
                "auth_required",
                False,
            )
        )

        return {
            "source": source_name,
            "source_title": getattr(
                metadata,
                "title",
                source_name,
            ),
            "dataset": dataset,
            "description_en": getattr(
                descriptor,
                "description_en",
                "",
            ),
            "description_ko": getattr(
                descriptor,
                "description_ko",
                "",
            ),
            "categories": list(categories),
            "canonical_metrics": canonical_metrics,
            "units": units,
            "artifact_kinds": artifact_kinds,
            "methods": methods,
            "available_start": available_start,
            "available_end": available_end,
            "availability_source": (availability_source),
            "live_availability_supported": (live_supported),
            "cadence": cadence,
            "data_scope": data_scope,
            "object_scope": object_scope,
            "objects": list(objects),
            "object_query_supported": (object_scope == "catalogue"),
            "authentication": source_auth,
            "auth_required": (
                descriptor_auth
                or source_auth
                not in {
                    "none",
                    "unknown",
                }
            ),
            "source_status": getattr(
                metadata,
                "status",
                "unknown",
            ),
            "homepage": getattr(
                metadata,
                "homepage",
                None,
            ),
            "availability_error": None,
        }

    def _live_discovery_state(
        self,
    ):
        cache = getattr(
            self,
            "_live_discovery_cache",
            None,
        )

        if cache is None:
            cache = {}
            self._live_discovery_cache = cache

        lock = getattr(
            self,
            "_live_discovery_lock",
            None,
        )

        if lock is None:
            lock = RLock()
            self._live_discovery_lock = lock

        return cache, lock

    def _live_dataset_row_cached(
        self,
        source_name: str,
        dataset: str,
    ) -> tuple[
        dict,
        bool,
    ]:
        """Return live metadata plus whether provider circuit should open."""

        cache, lock = self._live_discovery_state()

        adapter = self.get_source(source_name)

        key = (
            source_name,
            dataset,
            id(adapter),
        )

        now = monotonic()

        with lock:
            cached = cache.get(key)

            if cached is not None:
                expires_at, row, circuit = cached

                if expires_at > now:
                    return (
                        dict(row),
                        circuit,
                    )

                cache.pop(
                    key,
                    None,
                )

        circuit = False

        try:
            row = self._dataset_row(
                source_name,
                dataset,
                live=True,
            )

            ttl = _LIVE_DISCOVERY_SUCCESS_TTL

        except (
            OSError,
            requests.exceptions.RequestException,
            RuntimeError,
            TypeError,
            ValueError,
        ) as exc:
            row = self._dataset_row(
                source_name,
                dataset,
                live=False,
            )

            row["availability_error"] = f"{type(exc).__name__}: {exc}"

            # Open a provider-wide circuit only for connection-level
            # failures.  HTTP 4xx/5xx may be dataset-specific, so
            # those do not suppress other datasets.
            # requests.RequestException ultimately derives from
            # OSError, so a plain ``isinstance(exc, OSError)`` would
            # incorrectly classify HTTPError (including HTTP 4xx)
            # as a provider-wide connection failure.
            #
            # Open the circuit only for actual transport failures.
            circuit = isinstance(
                exc,
                (
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                ),
            ) or (
                isinstance(
                    exc,
                    OSError,
                )
                and not isinstance(
                    exc,
                    requests.exceptions.RequestException,
                )
            )

            ttl = _LIVE_DISCOVERY_ERROR_TTL

        with lock:
            cache[key] = (
                monotonic() + ttl,
                dict(row),
                circuit,
            )

        return row, circuit

    def _live_source_rows(
        self,
        source_name: str,
        rows: list[dict],
    ) -> list[dict]:
        """Enrich one source serially so one Session is never shared."""

        result = []
        circuit_error = None

        for base_row in rows:
            if circuit_error is not None:
                row = dict(base_row)

                row["availability_error"] = (
                    "CircuitOpen: live metadata "
                    "skipped after provider "
                    "connection failure: "
                    f"{circuit_error}"
                )

                result.append(row)
                continue

            row, opens_circuit = self._live_dataset_row_cached(
                source_name,
                base_row["dataset"],
            )

            result.append(row)

            if opens_circuit:
                circuit_error = row.get("availability_error")

        return result

    def datasets(
        self,
        *,
        source: str | None = None,
        metric: str | None = None,
        category: str | None = None,
        data_scope: str | None = None,
        object_scope: str | None = None,
        live: bool = False,
    ) -> list[dict]:
        """Return Orbitoby's curated dataset catalogue.

        Offline metadata is built and filtered first.  With
        ``live=True`` only the surviving rows perform provider
        metadata I/O.

        Live metadata lookup uses bounded source-level concurrency,
        a short-lived cache, and a connection-failure circuit
        breaker.  Provider failures remain explicit in each row.
        """

        if source is not None:
            source_names = (source,)

            # Validate source early.
            self.get_source(source)

        else:
            source_names = tuple(sorted(self.sources))

        candidates = []

        # ------------------------------------------------------
        # Filter pushdown:
        # construct local/offline rows first and avoid network
        # calls for datasets the caller will discard anyway.
        # ------------------------------------------------------

        for source_name in source_names:
            adapter = self.get_source(source_name)

            for dataset in adapter.datasets:
                row = self._dataset_row(
                    source_name,
                    dataset,
                    live=False,
                )

                if metric is not None and metric not in row["canonical_metrics"]:
                    continue

                if category is not None and category not in row["categories"]:
                    continue

                if data_scope is not None and row["data_scope"] != data_scope:
                    continue

                if object_scope is not None and row["object_scope"] != object_scope:
                    continue

                candidates.append(row)

        if not live:
            return sorted(
                candidates,
                key=lambda row: (
                    row["source"],
                    row["dataset"],
                ),
            )

        if not candidates:
            return []

        grouped = {}

        for row in candidates:
            grouped.setdefault(
                row["source"],
                [],
            ).append(row)

        source_items = list(grouped.items())

        if len(source_items) == 1:
            source_name, rows = source_items[0]

            result = self._live_source_rows(
                source_name,
                rows,
            )

        else:
            workers = min(
                _LIVE_DISCOVERY_MAX_WORKERS,
                len(source_items),
            )

            result = []

            # One worker per source keeps each adapter/session
            # single-threaded while allowing independent providers
            # to overlap their network wait time.
            with ThreadPoolExecutor(
                max_workers=workers,
                thread_name_prefix=("orbitoby-discovery"),
            ) as executor:
                futures = [
                    executor.submit(
                        self._live_source_rows,
                        source_name,
                        rows,
                    )
                    for (
                        source_name,
                        rows,
                    ) in source_items
                ]

                for future in futures:
                    result.extend(future.result())

        return sorted(
            result,
            key=lambda row: (
                row["source"],
                row["dataset"],
            ),
        )

    def dataset_info(
        self,
        source: str,
        dataset: str,
        *,
        live: bool = False,
    ) -> dict:
        """Return discovery metadata for one curated dataset."""

        return self._dataset_row(
            source,
            dataset,
            live=live,
        )

    def source_info(
        self,
        name: str | None = None,
    ):
        builtin = builtin_source_metadata()

        def info(
            source_name,
        ):
            adapter = self.get_source(source_name)

            metadata = getattr(
                adapter,
                "metadata",
                None,
            )

            if metadata is None:
                metadata = builtin.get(source_name)

            result = {}

            if metadata is not None:
                result.update(asdict(metadata))

            result["name"] = source_name
            result["datasets"] = list(adapter.datasets)

            return result

        if name is not None:
            return info(name)

        return [info(source_name) for source_name in sorted(self.sources)]

    def credits(
        self,
    ) -> list[dict]:
        result = []

        for source in self.source_info():
            result.append(
                {
                    "name": source["name"],
                    "title": source.get(
                        "title",
                        source["name"],
                    ),
                    "homepage": (source.get("homepage")),
                }
            )

        return result

    def licenses(
        self,
    ) -> list[dict]:
        result = []

        for source in self.source_info():
            policy = source.get("policy")

            result.append(
                {
                    "name": source["name"],
                    "policy": policy,
                }
            )

        return result

    def plugin_candidates(
        self,
    ) -> list[dict]:
        return [asdict(candidate) for candidate in discover_source_plugins()]

    def trust_source_plugin(
        self,
        name: str,
    ) -> list[str]:
        trust_plugin(name)

        return self.reload_sources()

    def untrust_source_plugin(
        self,
        name: str,
    ) -> list[str]:
        untrust_plugin(name)

        return self.reload_sources()

    def register_http_source(
        self,
        *,
        name: str,
        dataset: str,
        url: str,
        format: str = "json",
        root_key: str | None = None,
        homepage: str | None = None,
        description_en: str = "",
        description_ko: str = "",
    ) -> list[str]:
        register_http_source(
            name=name,
            dataset=dataset,
            url=url,
            format=format,
            root_key=root_key,
            homepage=homepage,
            description_en=(description_en),
            description_ko=(description_ko),
        )

        return self.reload_sources()

    def unregister_http_source(
        self,
        name: str,
        *,
        dataset: str | None = None,
    ) -> list[str]:
        unregister_http_source(
            name,
            dataset=dataset,
        )

        return self.reload_sources()
