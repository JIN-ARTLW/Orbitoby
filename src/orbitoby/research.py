from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

import pandas as pd

from orbitoby.canonical import (
    METRIC_BINDINGS,
    MetricBinding,
    adapter_metric_bindings,
    canonicalize_records,
)
from orbitoby.warehouse.scientific import ScientificStore

SCIENTIFIC_CACHE_TRANSFORM = "canonicalize_records"
SCIENTIFIC_CACHE_VERSION = "1"

ArtifactResolution = Literal[
    "all",
    "preferred",
]


@dataclass(slots=True)
class ResearchWindow:
    """Exact-timestamp research alignment without interpolation."""

    data: pd.DataFrame
    presence: pd.DataFrame
    missing_reason: pd.DataFrame
    provenance: pd.DataFrame
    units: dict[str, str]

    @property
    def metrics(self) -> tuple[str, ...]:
        return tuple(column for column in self.data.columns if column != "timestamp")

    def to_numpy(self):
        return self.data.loc[
            :,
            list(self.metrics),
        ].to_numpy()


class ResearchAPI:
    """High-level canonical research queries."""

    @staticmethod
    def _canonical_metric_name(
        field: str,
    ) -> str:
        if not isinstance(
            field,
            str,
        ):
            raise TypeError("Canonical field names must be strings.")

        result = field.strip()

        if not result:
            raise ValueError("Canonical field name must not be empty.")

        if result.startswith("space_weather."):
            return result[len("space_weather.") :]

        if result.startswith("thermosphere."):
            return "thermosphere_" + result[len("thermosphere.") :]

        return result

    @staticmethod
    def _utc_bound(
        value,
        *,
        name: str,
    ) -> pd.Timestamp:
        try:
            result = pd.Timestamp(value)
        except Exception as exc:
            raise ValueError(f"{name} is not a valid date/time.") from exc

        if result.tzinfo is None:
            return result.tz_localize("UTC")

        return result.tz_convert("UTC")

    def _active_metric_bindings(
        self,
    ) -> tuple[
        MetricBinding,
        ...,
    ]:
        """Return built-in plus active adapter-declared bindings."""

        result = list(METRIC_BINDINGS)

        sources = getattr(
            self,
            "sources",
            {},
        )

        for source_name in sorted(sources):
            result.extend(adapter_metric_bindings(sources[source_name]))

        return tuple(result)

    def _select_bindings(
        self,
        metric: str,
        *,
        source: str | None,
        source_preference: Iterable[str] | None,
        dataset: str | None,
    ) -> tuple[
        MetricBinding,
        ...,
    ]:
        active_bindings = self._active_metric_bindings()

        candidates = [
            binding for binding in active_bindings if binding.metric == metric
        ]

        if not candidates:
            available = ", ".join(
                sorted({binding.metric for binding in active_bindings})
            )

            raise ValueError(
                f"Unknown canonical metric: {metric!r}. Available metrics: {available}"
            )

        if dataset is not None:
            candidates = [
                binding for binding in candidates if binding.dataset == dataset
            ]

            if not candidates:
                raise ValueError(
                    f"No canonical binding "
                    f"for metric {metric!r} "
                    f"and dataset "
                    f"{dataset!r}."
                )

        if source is not None:
            candidates = [binding for binding in candidates if binding.source == source]

            if not candidates:
                raise ValueError(
                    f"Source {source!r} does not provide canonical metric {metric!r}."
                )

        elif source_preference is not None:
            preference = tuple(source_preference)

            selected = next(
                (
                    candidate_source
                    for candidate_source in preference
                    if any(binding.source == candidate_source for binding in candidates)
                ),
                None,
            )

            if selected is None:
                raise ValueError(
                    f"None of source_preference {preference!r} provides {metric!r}."
                )

            candidates = [
                binding for binding in candidates if binding.source == selected
            ]

        else:
            sources = {binding.source for binding in candidates}

            if len(sources) > 1:
                choices = ", ".join(sorted(sources))

                raise ValueError(
                    f"Metric {metric!r} "
                    f"has multiple sources "
                    f"({choices}). Specify "
                    "source= or "
                    "source_preference=."
                )

        if len(candidates) > 1 and not all(binding.mergeable for binding in candidates):
            datasets = ", ".join(sorted({binding.dataset for binding in candidates}))

            raise ValueError(
                f"Metric {metric!r} "
                "has multiple "
                "non-mergeable datasets: "
                f"{datasets}. Specify "
                "dataset= explicitly."
            )

        return tuple(
            sorted(
                candidates,
                key=lambda binding: (
                    binding.priority,
                    binding.source,
                    binding.dataset,
                ),
            )
        )

    @staticmethod
    def _canonical_frame(
        records,
        binding: MetricBinding,
        *,
        artifact,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        canonical = canonicalize_records(
            records,
            binding,
            artifact=artifact,
        )

        if not canonical:
            return pd.DataFrame()

        frame = pd.DataFrame(canonical)

        frame["timestamp"] = pd.to_datetime(
            frame["timestamp"],
            utc=True,
        )

        return frame[(frame["timestamp"] >= start) & (frame["timestamp"] < end)].copy()

    @staticmethod
    def _merge_ranges(
        ranges: list[
            tuple[
                pd.Timestamp,
                pd.Timestamp,
            ]
        ],
    ) -> list[
        tuple[
            pd.Timestamp,
            pd.Timestamp,
        ]
    ]:
        if not ranges:
            return []

        ordered = sorted(
            ranges,
            key=lambda item: (
                item[0],
                item[1],
            ),
        )

        merged = [ordered[0]]

        for start, end in ordered[1:]:
            previous_start, previous_end = merged[-1]

            if start <= previous_end:
                merged[-1] = (
                    previous_start,
                    max(
                        previous_end,
                        end,
                    ),
                )
            else:
                merged.append(
                    (
                        start,
                        end,
                    )
                )

        return merged

    @staticmethod
    def _range_intersections(
        *,
        start: pd.Timestamp,
        end: pd.Timestamp,
        ranges: list[
            tuple[
                pd.Timestamp,
                pd.Timestamp,
            ]
        ],
    ) -> list[
        tuple[
            pd.Timestamp,
            pd.Timestamp,
        ]
    ]:
        intersections = []

        for range_start, range_end in ranges:
            overlap_start = max(
                start,
                range_start,
            )
            overlap_end = min(
                end,
                range_end,
            )

            if overlap_start < overlap_end:
                intersections.append(
                    (
                        overlap_start,
                        overlap_end,
                    )
                )

        return intersections

    def _fetch_binding_group(
        self,
        bindings: list[MetricBinding],
        *,
        start: pd.Timestamp,
        end: pd.Timestamp,
        archive_raw: bool,
    ) -> list[pd.DataFrame]:
        first = bindings[0]

        params = {}

        if first.fetch_window:
            params["start"] = start.to_pydatetime()
            params["end"] = end.to_pydatetime()

        records, artifact = self._fetch_records(
            source=first.source,
            dataset=first.dataset,
            archive_raw=archive_raw,
            **params,
        )

        frames: list[pd.DataFrame] = []

        for binding in bindings:
            frame = self._canonical_frame(
                records,
                binding,
                artifact=artifact,
                start=start,
                end=end,
            )

            if not frame.empty:
                frames.append(frame)

        return frames

    def _cached_binding_group(
        self,
        bindings: list[MetricBinding],
        *,
        start: pd.Timestamp,
        end: pd.Timestamp,
        archive_raw: bool,
    ) -> list[pd.DataFrame]:
        store = getattr(
            self,
            "scientific_store",
            None,
        )

        if not archive_raw or not isinstance(
            store,
            ScientificStore,
        ):
            return self._fetch_binding_group(
                bindings,
                start=start,
                end=end,
                archive_raw=archive_raw,
            )

        first = bindings[0]

        binding_missing = []

        for binding in bindings:
            missing = store.missing_ranges(
                metric=binding.metric,
                source=binding.source,
                dataset=binding.dataset,
                transform=(SCIENTIFIC_CACHE_TRANSFORM),
                transform_version=(SCIENTIFIC_CACHE_VERSION),
                start=start,
                end=end,
            )

            binding_missing.append(
                (
                    binding,
                    missing,
                )
            )

        fetch_ranges = self._merge_ranges(
            [interval for _, ranges in binding_missing for interval in ranges]
        )

        for fetch_start, fetch_end in fetch_ranges:
            params = {}

            if first.fetch_window:
                params["start"] = fetch_start.to_pydatetime()
                params["end"] = fetch_end.to_pydatetime()

            records, artifact = self._fetch_records(
                source=first.source,
                dataset=first.dataset,
                archive_raw=True,
                **params,
            )

            if artifact is None:
                raise RuntimeError("Canonical persistence requires a raw artifact.")

            for binding, missing in binding_missing:
                intersections = self._range_intersections(
                    start=fetch_start,
                    end=fetch_end,
                    ranges=missing,
                )

                for (
                    interval_start,
                    interval_end,
                ) in intersections:
                    frame = self._canonical_frame(
                        records,
                        binding,
                        artifact=artifact,
                        start=interval_start,
                        end=interval_end,
                    )

                    if frame.empty:
                        store.record_coverage(
                            metric=(binding.metric),
                            source=(binding.source),
                            dataset=(binding.dataset),
                            artifact_id=(artifact.artifact_id),
                            transform=(SCIENTIFIC_CACHE_TRANSFORM),
                            transform_version=(SCIENTIFIC_CACHE_VERSION),
                            requested_start=(interval_start),
                            requested_end=(interval_end),
                            row_count=0,
                            store_id=None,
                        )

                        continue

                    saved = store.write(
                        frame,
                        requested_start=(interval_start),
                        requested_end=(interval_end),
                    )

                    store.record_coverage(
                        metric=binding.metric,
                        source=binding.source,
                        dataset=binding.dataset,
                        artifact_id=(artifact.artifact_id),
                        transform=(SCIENTIFIC_CACHE_TRANSFORM),
                        transform_version=(SCIENTIFIC_CACHE_VERSION),
                        requested_start=(interval_start),
                        requested_end=(interval_end),
                        row_count=len(frame),
                        store_id=(saved.store_id),
                    )

        frames = []

        for binding in bindings:
            frame = store.query_coverage(
                metric=binding.metric,
                source=binding.source,
                dataset=binding.dataset,
                transform=(SCIENTIFIC_CACHE_TRANSFORM),
                transform_version=(SCIENTIFIC_CACHE_VERSION),
                start=start,
                end=end,
            )

            if frame.empty:
                continue

            frame["_binding_priority"] = binding.priority

            frames.append(frame)

        return frames

    def timeseries(
        self,
        metric: str | None = None,
        *,
        fields: Iterable[str] | str | None = None,
        start,
        end,
        source: str | None = None,
        source_preference: Iterable[str] | None = None,
        dataset: str | None = None,
        artifact_resolution: ArtifactResolution = ("all"),
        archive_raw: bool = True,
    ) -> pd.DataFrame:
        """Return provenance-rich canonical scientific series."""

        if metric is not None and fields is not None:
            raise ValueError("Use either metric= or fields=, not both.")

        if metric is None and fields is None:
            raise ValueError("metric or fields is required.")

        if artifact_resolution not in {
            "all",
            "preferred",
        }:
            raise ValueError("artifact_resolution must be 'all' or 'preferred'.")

        start_ts = self._utc_bound(
            start,
            name="start",
        )

        end_ts = self._utc_bound(
            end,
            name="end",
        )

        if start_ts >= end_ts:
            raise ValueError("start must be before end.")

        if metric is not None:
            requested = (metric,)

        elif isinstance(
            fields,
            str,
        ):
            requested = (fields,)

        else:
            requested = tuple(fields or ())

        if not requested:
            raise ValueError("fields must not be empty.")

        selected: list[MetricBinding] = []

        for requested_field in requested:
            canonical_metric = self._canonical_metric_name(requested_field)

            for binding in self._select_bindings(
                canonical_metric,
                source=source,
                source_preference=(source_preference),
                dataset=dataset,
            ):
                if binding not in selected:
                    selected.append(binding)

        groups: dict[
            tuple[
                str,
                str,
                bool,
            ],
            list[MetricBinding],
        ] = defaultdict(list)

        for binding in selected:
            groups[
                (
                    binding.source,
                    binding.dataset,
                    binding.fetch_window,
                )
            ].append(binding)

        frames: list[pd.DataFrame] = []

        for bindings in groups.values():
            frames.extend(
                self._cached_binding_group(
                    bindings,
                    start=start_ts,
                    end=end_ts,
                    archive_raw=(archive_raw),
                )
            )

        columns = [
            "timestamp",
            "metric",
            "value",
            "unit",
            "source_value",
            "is_missing",
            "missing_reason",
            "source",
            "dataset",
            "source_field",
            "source_version",
            "status",
            "provider_status",
            "quality_flag",
            "artifact_kind",
            "method",
            "interval_start",
            "interval_end",
            "artifact_id",
            "retrieved_at",
            "transform",
            "transform_version",
            "context",
        ]

        if not frames:
            return pd.DataFrame(columns=columns)

        result = pd.concat(
            frames,
            ignore_index=True,
        )

        result = result.sort_values(
            [
                "metric",
                "timestamp",
                "source",
                "_binding_priority",
                "dataset",
            ]
        ).reset_index(drop=True)

        if artifact_resolution == "preferred":
            result = result.drop_duplicates(
                subset=[
                    "metric",
                    "timestamp",
                    "source",
                ],
                keep="first",
            ).reset_index(drop=True)

            result["selection_rule"] = "provider_artifact_priority_v1"

        return result.drop(columns=["_binding_priority"])

    def window(
        self,
        *,
        start,
        end,
        fields: Iterable[str] | str,
        source: str | None = None,
        source_preference: Iterable[str] | None = None,
        dataset: str | None = None,
        artifact_resolution: ArtifactResolution = "all",
        archive_raw: bool = True,
    ) -> ResearchWindow:
        """
        Align canonical series on exact observed timestamps.

        No interpolation, smoothing, resampling,
        forward-fill, averaging, or implicit conflict
        resolution is performed.
        """

        if isinstance(
            fields,
            str,
        ):
            requested = (fields,)
        else:
            requested = tuple(fields)

        if not requested:
            raise ValueError("fields must not be empty.")

        metrics = []

        for field in requested:
            metric = self._canonical_metric_name(field)

            if metric not in metrics:
                metrics.append(metric)

        provenance = self.timeseries(
            fields=requested,
            start=start,
            end=end,
            source=source,
            source_preference=(source_preference),
            dataset=dataset,
            artifact_resolution=(artifact_resolution),
            archive_raw=archive_raw,
        )

        timestamp_columns = [
            "timestamp",
            *metrics,
        ]

        if provenance.empty:
            empty_values = pd.DataFrame(columns=timestamp_columns)

            empty_presence = pd.DataFrame(columns=timestamp_columns)

            empty_missing = pd.DataFrame(columns=timestamp_columns)

            return ResearchWindow(
                data=empty_values,
                presence=empty_presence,
                missing_reason=empty_missing,
                provenance=provenance,
                units={},
            )

        working = provenance.copy()

        working["timestamp"] = pd.to_datetime(
            working["timestamp"],
            utc=True,
            errors="raise",
        )

        units = {}

        for metric in metrics:
            metric_rows = working[working["metric"] == metric]

            metric_units = tuple(
                sorted({str(value) for value in (metric_rows["unit"].dropna())})
            )

            if len(metric_units) > 1:
                raise ValueError(
                    "window() cannot align "
                    f"metric {metric!r} with "
                    "multiple units: " + ", ".join(metric_units)
                )

            if metric_units:
                units[metric] = metric_units[0]

        duplicates = working.duplicated(
            subset=[
                "metric",
                "timestamp",
            ],
            keep=False,
        )

        if duplicates.any():
            conflicts = working.loc[
                duplicates,
                [
                    "metric",
                    "timestamp",
                    "source",
                    "dataset",
                    "artifact_id",
                ],
            ].sort_values(
                [
                    "metric",
                    "timestamp",
                    "source",
                    "dataset",
                    "artifact_id",
                ],
                kind="stable",
            )

            first = conflicts.iloc[0]

            raise ValueError(
                "window() requires exactly "
                "one canonical row per "
                "metric/timestamp. Conflict at "
                f"{first['metric']!r} / "
                f"{first['timestamp']}. "
                "Specify source/dataset or use "
                "an explicit artifact resolution."
            )

        timestamps = (
            working["timestamp"]
            .drop_duplicates()
            .sort_values(kind="stable")
            .reset_index(drop=True)
        )

        base = pd.DataFrame(
            {
                "timestamp": timestamps,
            }
        )

        values = (
            working.pivot(
                index="timestamp",
                columns="metric",
                values="value",
            )
            .reindex(columns=metrics)
            .reset_index()
        )

        presence_source = working.assign(_present=True)

        presence = (
            presence_source.pivot(
                index="timestamp",
                columns="metric",
                values="_present",
            )
            .reindex(columns=metrics)
            .reindex(timestamps)
            .fillna(False)
            .astype(bool)
            .reset_index()
        )

        missing = (
            working.pivot(
                index="timestamp",
                columns="metric",
                values="missing_reason",
            )
            .reindex(columns=metrics)
            .reindex(timestamps)
            .reset_index()
        )

        values = base[["timestamp"]].merge(
            values,
            on="timestamp",
            how="left",
            validate="one_to_one",
        )

        presence = base[["timestamp"]].merge(
            presence,
            on="timestamp",
            how="left",
            validate="one_to_one",
        )

        missing = base[["timestamp"]].merge(
            missing,
            on="timestamp",
            how="left",
            validate="one_to_one",
        )

        return ResearchWindow(
            data=values,
            presence=presence,
            missing_reason=missing,
            provenance=working,
            units=units,
        )

    def space_weather(
        self,
        *,
        start,
        end,
        fields: Iterable[str] | str,
        source: str | None = None,
        source_preference: Iterable[str] | None = None,
        dataset: str | None = None,
        artifact_resolution: ArtifactResolution = ("all"),
        archive_raw: bool = True,
    ) -> pd.DataFrame:
        return self.timeseries(
            fields=fields,
            start=start,
            end=end,
            source=source,
            source_preference=(source_preference),
            dataset=dataset,
            artifact_resolution=(artifact_resolution),
            archive_raw=archive_raw,
        )
