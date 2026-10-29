"""Exact-time alignment without interpolation or identity blending."""

import json
from pathlib import Path

import pandas as pd

from orbitoby._easy_result import DataResult, SourceList


def _utc(value):
    result = pd.Timestamp(value)
    if result.tzinfo is None:
        return result.tz_localize("UTC")
    return result.tz_convert("UTC")


def _identity(value, default="not declared"):
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    return str(value)


class AlignedResult(DataResult):
    """Exact UTC union of multiple independently sourced results."""

    def __init__(
        self,
        table,
        *,
        provenance,
        presence,
        missing_reason,
        series_info,
        originals,
    ):
        first = originals[0]
        super().__init__(
            table,
            name="Exact UTC time alignment",
            start=first.start,
            end=first.end,
            source="explicit input results",
        )
        self._provenance = provenance
        self._presence = presence
        self._missing_reason = missing_reason
        self.series_info = series_info
        self._originals = originals

    @property
    def provenance(self):
        return self._provenance.copy()

    @property
    def presence(self):
        return self._presence.copy()

    @property
    def missing_reason(self):
        return self._missing_reason.copy()

    def info(self):
        print("Alignment: exact UTC timestamp union")
        print("Period:", self.start, "to", self.end, "(end excluded)")
        print("Unique timestamps:", len(self._frame))
        print("Series:", len(self.series_info))
        print("Interpolation: none")
        print("Resampling: none")
        print("Orbit propagation: none")

        for name, details in self.series_info.items():
            print(
                name,
                "|",
                details["representation"],
                "|",
                details["unit"],
            )
        return self

    def sources(self):
        rows = pd.DataFrame(
            [
                {
                    "metric": spec["metric"],
                    "source": spec["source"],
                    "dataset": spec["dataset"],
                }
                for spec in self.series_info.values()
            ]
        )
        return SourceList(rows, "explicit alignment")

    def plot(self, *args, **kwargs):
        raise ValueError(
            "This alignment may contain incompatible quantities or "
            "orbit element records. Plot the original scientific "
            "results with result.plot() instead."
        )

    def save(self, filename):
        path = Path(filename)

        if path.suffix.lower() != ".csv":
            raise ValueError("Use a .csv filename.")

        self._frame.to_csv(path, index=False)

        self._presence.to_csv(
            path.with_name(path.stem + "_presence.csv"),
            index=False,
        )

        self._missing_reason.to_csv(
            path.with_name(path.stem + "_missing.csv"),
            index=False,
        )

        # Export explicit safe fields, never raw context or URLs.
        safe = (
            "_alignment_timestamp",
            "_alignment_series",
            "timestamp",
            "epoch",
            "EPOCH",
            "norad_id",
            "NORAD_CAT_ID",
            "metric",
            "source",
            "dataset",
            "value",
            "unit",
            "artifact_id",
            "product_id",
            "artifact_kind",
            "quality_flag",
            "is_missing",
            "missing_reason",
        )

        columns = [name for name in safe if name in self._provenance.columns]

        self._provenance[columns].to_csv(
            path.with_name(path.stem + "_provenance.csv"),
            index=False,
        )

        metadata = {
            "alignment": "exact UTC timestamp union",
            "interpolation": "none",
            "resampling": "none",
            "orbit_propagation": "none",
            "series": self.series_info,
        }

        path.with_name(path.stem + "_metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return path


def align_results(*items):
    """Align canonical series and orbital-element epoch records."""
    if len(items) < 2:
        raise ValueError("Provide at least two results: study.align(a, b).")

    if not all(isinstance(item, DataResult) for item in items):
        raise TypeError("study.align() requires Orbitoby results.")

    start = _utc(items[0].start)
    end = _utc(items[0].end)

    frames = []

    for index, item in enumerate(items, start=1):
        if _utc(item.start) != start or _utc(item.end) != end:
            raise ValueError("All aligned results must have the same period.")

        frame = (item.provenance if hasattr(item, "_window") else item.table).copy()

        if frame.empty:
            raise ValueError(f"Result {index} contains no records.")

        time_fields = [
            name for name in ("timestamp", "epoch", "EPOCH") if name in frame.columns
        ]

        if not time_fields:
            raise ValueError(
                f"Result {index} has no timestamp or orbital element epoch."
            )

        frame["_alignment_timestamp"] = pd.to_datetime(
            frame[time_fields[0]],
            utc=True,
            errors="raise",
        )

        times = frame["_alignment_timestamp"]

        if times.isna().any() or ((times < start) | (times >= end)).any():
            raise ValueError(
                f"Result {index} contains invalid or out-of-period timestamps."
            )

        id_field = next(
            (key for key in ("norad_id", "NORAD_CAT_ID") if key in frame.columns),
            None,
        )

        keys = []

        for _, row in frame.iterrows():
            key = (
                index,
                _identity(
                    row.get("metric"),
                    "orbital element epoch",
                ),
                _identity(
                    row.get("source"),
                    item.requested_source,
                ),
                _identity(row.get("dataset")),
                (_identity(row.get(id_field)) if id_field else None),
            )

            keys.append(json.dumps(key, ensure_ascii=False))

        frame["_alignment_series"] = keys

        # Determine the representation BEFORE concatenating
        # heterogeneous scientific result schemas.
        frame["_alignment_kind"] = (
            "scalar"
            if {"metric", "value", "unit"}.issubset(frame.columns)
            else "record"
        )

        frames.append(frame)

    provenance = pd.concat(
        frames,
        ignore_index=True,
        sort=False,
    )

    timeline = pd.DatetimeIndex(
        provenance["_alignment_timestamp"].drop_duplicates().sort_values()
    )

    table = pd.DataFrame({"timestamp": timeline})
    presence = pd.DataFrame({"timestamp": timeline})
    missing = pd.DataFrame({"timestamp": timeline})

    series_info = {}

    for key, group in provenance.groupby(
        "_alignment_series",
        sort=False,
    ):
        indexed = group.set_index("_alignment_timestamp")

        if indexed.index.has_duplicates:
            raise ValueError(
                "Duplicate records for the same "
                "timestamp, metric, provider, dataset "
                "and NORAD identity. Resolve the product "
                "or artifact conflict explicitly."
            )

        _, metric, source, dataset, norad = json.loads(key)

        kinds = group["_alignment_kind"].dropna().unique()

        if len(kinds) != 1:
            raise ValueError(
                "Conflicting representations within one scientific alignment series."
            )

        scalar = kinds[0] == "scalar"

        units = (
            group["unit"].dropna().astype(str).unique()
            if "unit" in group.columns
            else []
        )

        if len(units) > 1:
            raise ValueError(f"{metric}: conflicting units in one series.")

        unit = units[0] if len(units) else "not declared"

        number = len(series_info) + 1
        suffix = f"; NORAD {norad}" if norad else ""

        label = f"[{number}] {metric} ({source}/{dataset}{suffix})"

        present = timeline.isin(indexed.index)
        presence[label] = present

        explanations = pd.Series(
            None,
            index=timeline,
            dtype=object,
        )

        if scalar:
            values = indexed["value"].reindex(timeline)

            if "is_missing" in indexed.columns:
                flagged = (
                    indexed["is_missing"]
                    .fillna(False)
                    .astype(bool)
                    .reindex(timeline, fill_value=False)
                )
            else:
                flagged = pd.Series(False, index=timeline)

            table[label] = values.mask(flagged).to_numpy()

            explanations.iloc[~present] = "no record at exact UTC timestamp"

            invalid = present & (flagged.to_numpy() | values.isna().to_numpy())

            explanations.iloc[invalid] = "reported missing or null"

            if "missing_reason" in indexed.columns:
                reasons = indexed["missing_reason"].reindex(timeline)

                explanations.iloc[invalid] = [
                    _identity(value, "reported missing or null")
                    for value in reasons.iloc[invalid]
                ]

            representation = "scalar value"

        else:
            # An orbital element epoch is a record, not a
            # scalar measurement or propagated position.
            table[label] = present.astype(int)
            explanations.iloc[~present] = "no orbital element epoch record"
            representation = "record count"
            unit = "records"
            label = str(label)

        missing[label] = explanations.to_numpy()

        series_info[label] = {
            "metric": metric,
            "source": source,
            "dataset": dataset,
            "norad_id": norad,
            "unit": unit,
            "representation": representation,
        }

    return AlignedResult(
        table,
        provenance=provenance,
        presence=presence,
        missing_reason=missing,
        series_info=series_info,
        originals=tuple(items),
    )
