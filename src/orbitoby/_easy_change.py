"""Explicit first differences over actually observed UTC timestamps."""

import pandas as pd

from orbitoby._easy_result import DataResult

_GROUP_FIELDS = (
    "norad_id",
    "source",
    "dataset",
    "metric",
    "unit",
    "platform",
    "mission",
    "instrument",
    "model_name",
    "model_version",
    "product_version",
    "data_role",
)

_PARENT_FIELDS = (
    "record_id",
    "artifact_id",
    "source",
    "dataset",
    "norad_id",
)


class ChangeResult(DataResult):
    """Derived values and the exact input record references used."""

    def __init__(self, frame, *, original, parents, method, field):
        super().__init__(
            frame,
            name=f"{field} {method}",
            start=original.start,
            end=original.end,
            source=original.requested_source,
        )
        self._raw_artifact_ids = tuple(getattr(original, "_raw_artifact_ids", ()))
        self._native_lineage_only = getattr(original, "_native_lineage_only", False)
        self.method = method
        self.field = field
        self._parents = parents.copy(deep=True)

    @property
    def provenance(self):
        """Expose only internally verified raw-request lineage."""
        return super().provenance

    def info(self, topic=None):
        if topic is not None:
            return super().info(topic)

        super().info()
        print("Data role: orbitoby_derived")
        print("Transformation:", self.method)
        print("Input field:", self.field)
        print("Difference: current observed value minus previous observed value")
        print("Rate denominator: actual elapsed UTC seconds")
        print("Missing values: no pair is calculated across a missing value")
        print("Interpolation: none")
        print("Input lineage: preserved when input IDs are available")
        return self


def change_result(result, field=None, **options):
    method = options.pop("method", "difference")

    if options:
        raise TypeError("Unknown change options: " + ", ".join(sorted(options)))

    if method not in ("difference", "rate"):
        raise ValueError("method must be 'difference' or 'rate'.")

    frame = result.table.copy(deep=True)

    if field is None:
        field = "value"

    if not isinstance(field, str) or not field.strip():
        raise ValueError("field must be a non-empty column name.")

    selected = field if field in frame else field.strip().replace(" ", "_")

    if selected not in frame:
        raise ValueError(
            f"Column {field!r} is not available. "
            f"Available columns: {', '.join(map(str, frame.columns))}"
        )

    if not pd.api.types.is_numeric_dtype(frame[selected]):
        raise TypeError("Change requires a numeric data column.")

    if pd.api.types.is_bool_dtype(frame[selected]):
        raise TypeError("Boolean values are not measurable changes.")

    time_field = next(
        (key for key in ("timestamp", "epoch") if key in frame),
        None,
    )

    if time_field is None:
        raise ValueError("Change requires actual timestamp or epoch values.")

    if frame.empty:
        parsed = pd.Series(dtype="datetime64[ns, UTC]")
    else:
        parsed = pd.to_datetime(frame[time_field], errors="raise")

    if not isinstance(parsed.dtype, pd.DatetimeTZDtype):
        raise TypeError(
            "Change requires timezone-aware timestamps; "
            "naive dates are not silently treated as UTC."
        )

    if parsed.isna().any():
        raise ValueError("Change cannot use missing timestamps.")

    frame["_orbitoby_utc"] = parsed.dt.tz_convert("UTC")

    group_fields = [name for name in _GROUP_FIELDS if name in frame]

    if group_fields:
        groups = frame.groupby(
            group_fields,
            sort=False,
            dropna=False,
        )
    else:
        groups = [(None, frame)]

    output = []
    parent_rows = []

    for _, group in groups:
        ordered = group.sort_values(
            "_orbitoby_utc",
            kind="stable",
        ).reset_index(drop=True)

        if ordered["_orbitoby_utc"].duplicated().any():
            raise ValueError(
                "Duplicate epochs within one physical series. "
                "Resolve the duplicates before calculating changes."
            )

        for index in range(1, len(ordered)):
            previous = ordered.iloc[index - 1]
            current = ordered.iloc[index]

            first = previous[selected]
            second = current[selected]

            if pd.isna(first) or pd.isna(second):
                continue

            seconds = (
                current["_orbitoby_utc"] - previous["_orbitoby_utc"]
            ).total_seconds()

            if seconds <= 0:
                raise ValueError("Change requires strictly increasing observed times.")

            difference = float(second) - float(first)
            computed = difference / seconds if method == "rate" else difference

            original_unit = current.get("unit")
            unit = (
                str(original_unit)
                if original_unit is not None and pd.notna(original_unit)
                else "not declared"
            )

            if method == "rate" and unit != "not declared":
                unit = f"{unit}/s"

            row = {
                name: current[name]
                for name in group_fields
                if name not in ("metric", "unit", "data_role")
            }

            row.update(
                timestamp=current["_orbitoby_utc"],
                metric=f"{selected}_{method}",
                value=computed,
                unit=unit,
                data_role="orbitoby_derived",
                transform=f"observed_first_{method}",
                interval_seconds=seconds,
            )

            output.append(row)

            for parent in (previous, current):
                reference = {
                    name: parent[name]
                    for name in _PARENT_FIELDS
                    if name in parent and pd.notna(parent[name])
                }

                if "record_id" in reference or "artifact_id" in reference:
                    parent_rows.append(reference)

    result_frame = pd.DataFrame(
        output,
        columns=[
            *[
                name
                for name in group_fields
                if name not in ("metric", "unit", "data_role")
            ],
            "timestamp",
            "metric",
            "value",
            "unit",
            "data_role",
            "transform",
            "interval_seconds",
        ],
    )

    parents = pd.DataFrame(parent_rows).drop_duplicates()

    return ChangeResult(
        result_frame,
        original=result,
        parents=parents,
        method=method,
        field=selected,
    )
