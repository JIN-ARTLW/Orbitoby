"""Explicit record-time coverage summaries without inferred cadence."""

import pandas as pd

from orbitoby._easy_discovery import CatalogList


def _utc_timestamps(values):
    nonmissing = values.dropna()

    if nonmissing.empty:
        return pd.Series(dtype="datetime64[ns, UTC]")

    parsed = pd.to_datetime(nonmissing, errors="raise")

    if not isinstance(parsed.dtype, pd.DatetimeTZDtype):
        raise TypeError(
            "Coverage timestamps must declare a timezone. "
            "Timezone-naive values cannot silently become UTC."
        )

    return parsed.dt.tz_convert("UTC")


def result_coverage(result):
    """Summarize returned timestamps, not cached archive coverage."""
    frame = result.table

    time_column = next(
        (name for name in ("timestamp", "epoch") if name in frame.columns),
        None,
    )

    if time_column is None:
        return CatalogList(
            [
                {
                    "scope": "returned-result",
                    "status": "not_temporal",
                    "rows": len(frame),
                    "coverage_fraction": None,
                    "definition": (
                        "No timestamp or epoch column. "
                        "Temporal coverage is not applicable."
                    ),
                }
            ],
            title="Result time coverage",
        )

    groups = (
        frame.groupby("norad_id", dropna=False, sort=False)
        if "norad_id" in frame.columns
        else [(None, frame)]
    )

    summaries = []

    for norad_id, group in groups:
        timestamps = _utc_timestamps(group[time_column])

        observed_days = (
            timestamps.dt.normalize().nunique() if not timestamps.empty else 0
        )

        summaries.append(
            {
                "scope": "returned-result",
                "norad_id": norad_id,
                "time_column": time_column,
                "rows": len(group),
                "rows_with_time": len(timestamps),
                "unique_epochs": timestamps.nunique(),
                "observed_utc_days": observed_days,
                "first_epoch_utc": (
                    timestamps.min().isoformat() if not timestamps.empty else None
                ),
                "last_epoch_utc": (
                    timestamps.max().isoformat() if not timestamps.empty else None
                ),
                "coverage_fraction": None,
                "definition": (
                    "Actual timestamps in returned records only; "
                    "not archive cache coverage or the "
                    "orbit.check observed-date ratio. "
                    "No interpolation or cadence assumption."
                ),
            }
        )

    if not summaries:
        summaries.append(
            {
                "scope": "returned-result",
                "rows": 0,
                "rows_with_time": 0,
                "unique_epochs": 0,
                "observed_utc_days": 0,
                "coverage_fraction": None,
                "definition": "No returned records; coverage unknown.",
            }
        )

    return CatalogList(
        summaries,
        title="Actual result-record time coverage",
    )
