"""Plot historical orbital-element epochs without propagation."""

import pandas as pd

from orbitoby._easy_result import DataResult

_FIELDS = {
    "periapsis": ("periapsis_km", "km"),
    "perigee": ("periapsis_km", "km"),
    "periapsis_km": ("periapsis_km", "km"),
    "apoapsis": ("apoapsis_km", "km"),
    "apogee": ("apoapsis_km", "km"),
    "apoapsis_km": ("apoapsis_km", "km"),
    "inclination": ("inclination_deg", "deg"),
    "inclination_deg": ("inclination_deg", "deg"),
    "mean motion": ("mean_motion", "rev/day"),
    "mean_motion": ("mean_motion", "rev/day"),
    "eccentricity": ("eccentricity", "1"),
}


def plot_orbit(
    result,
    field="periapsis",
    *,
    kind="scatter",
    title=None,
    width=900,
    height=360,
):
    if not isinstance(field, str):
        raise TypeError("Orbit field must be a string.")

    key = field.strip().lower().replace("-", "_")

    if key not in _FIELDS:
        raise ValueError(
            f"Unknown orbital element {field!r}. "
            "Try periapsis, apoapsis, inclination, "
            "mean motion or eccentricity."
        )

    column, unit = _FIELDS[key]
    original = result.table

    if original.empty:
        raise ValueError("No historical orbital epochs to plot.")

    if column not in original:
        raise ValueError(
            f"Orbital element {column!r} is unavailable. "
            f"Available columns: {', '.join(original.columns)}"
        )

    time_column = next(
        (name for name in ("epoch", "EPOCH", "timestamp") if name in original),
        None,
    )

    if time_column is None:
        raise ValueError("Orbit records have no element epoch.")

    frame = original.reset_index(drop=True).copy()

    timestamps = pd.to_datetime(frame[time_column], utc=True, errors="raise")

    if timestamps.isna().any():
        raise ValueError("Orbit data contains invalid epochs.")

    start = pd.Timestamp(result.start, tz="UTC")
    end = pd.Timestamp(result.end, tz="UTC")

    if ((timestamps < start) | (timestamps >= end)).any():
        raise ValueError("Orbit epochs fall outside the study period.")

    if "norad_id" not in frame:
        if "NORAD_CAT_ID" in frame:
            frame["norad_id"] = frame["NORAD_CAT_ID"]
        elif len(result._norad_ids) == 1:
            frame["norad_id"] = result._norad_ids[0]
        else:
            raise ValueError("Multiple spacecraft require explicit NORAD IDs.")

    if frame["norad_id"].isna().any():
        raise ValueError("Orbit records contain missing NORAD IDs.")

    frame["timestamp"] = timestamps
    frame["metric"] = column
    frame["value"] = pd.to_numeric(frame[column], errors="raise")
    frame["unit"] = unit

    if "source" not in frame:
        frame["source"] = result.requested_source

    if "dataset" not in frame:
        frame["dataset"] = "gp_history"

    if frame.duplicated(["timestamp", "norad_id", "source", "dataset"]).any():
        raise ValueError(
            "Multiple orbital records share the same epoch, "
            "NORAD ID and source/product. Resolve the conflict "
            "explicitly before plotting."
        )

    frame["plot_label"] = (
        frame["source"].astype(str)
        + " / "
        + frame["dataset"].astype(str)
        + " · NORAD "
        + frame["norad_id"].astype(str)
    )

    data = DataResult(
        frame,
        name=f"Historical orbit: {column}",
        start=result.start,
        end=result.end,
        source=result.requested_source,
    )

    # Retain only the parent result's internally verified raw lineage.
    # Never infer verified IDs from provider-supplied data columns.
    data._raw_artifact_ids = tuple(getattr(result, "_raw_artifact_ids", ()))

    if kind == "auto":
        kind = "scatter"

    if kind not in {"scatter", "line"}:
        raise ValueError("Choose kind='scatter' or kind='line'.")

    return data.plot(
        kind=kind,
        title=title or f"Historical orbital element: {column}",
        width=width,
        height=height,
    )
