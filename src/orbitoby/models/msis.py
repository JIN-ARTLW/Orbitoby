from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import pandas as pd

MODEL_NAME = "NRLMSIS"
MODEL_VERSION = "2.1"
TRANSFORM = "nrlmsis_density"
TRANSFORM_VERSION = "1"

DATASET = "nrlmsis_2_1_density"
METRIC = "thermosphere_neutral_mass_density"
UNIT = "kg/m^3"
METHOD = "nrlmsis_2_1"


MSIS_INPUT_COLUMNS = (
    "timestamp",
    "longitude_deg",
    "latitude_deg",
    "altitude_km",
    "f107_previous_day_sfu",
    "f107a_81day_centered_sfu",
    "ap_daily",
    "ap_current_3h",
    "ap_3h_prior",
    "ap_6h_prior",
    "ap_9h_prior",
    "ap_12_33h_avg",
    "ap_36_57h_avg",
)


@dataclass(frozen=True, slots=True)
class MSISRun:
    data: pd.DataFrame
    model_name: str
    model_version: str
    backend: str
    backend_version: str
    geomagnetic_activity: int
    interpolate_indices: bool


def build_msis_inputs(
    trajectory: pd.DataFrame,
    *,
    f107: pd.DataFrame,
    ap_daily: pd.DataFrame,
    ap_3h: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build explicit NRLMSIS forcing on an existing trajectory.

    This transform performs only model-defined forcing construction:

    - previous-day daily F10.7
    - centered 81-day daily F10.7 mean
    - exact 3-hour Ap vector
    - exact 12--33 h and 36--57 h Ap means

    No interpolation, forward-fill, backward-fill, resampling,
    nearest-time matching, or implicit source selection occurs.
    """

    trajectory_columns = {
        "timestamp",
        "longitude_deg",
        "latitude_deg",
        "altitude_km",
    }

    if not isinstance(
        trajectory,
        pd.DataFrame,
    ):
        raise TypeError("trajectory must be a pandas DataFrame.")

    if trajectory.empty:
        raise ValueError("trajectory must not be empty.")

    missing = trajectory_columns - set(trajectory.columns)

    if missing:
        raise ValueError("trajectory is missing: " + ", ".join(sorted(missing)))

    result = trajectory.loc[
        :,
        [
            "timestamp",
            "longitude_deg",
            "latitude_deg",
            "altitude_km",
        ],
    ].copy()

    result["timestamp"] = pd.to_datetime(
        result["timestamp"],
        utc=True,
        errors="raise",
    )

    if result["timestamp"].duplicated().any():
        raise ValueError("trajectory contains duplicate timestamps.")

    for column in (
        "longitude_deg",
        "latitude_deg",
        "altitude_km",
    ):
        result[column] = pd.to_numeric(
            result[column],
            errors="raise",
        )

        if result[column].isna().any():
            raise ValueError(f"{column} contains missing values.")

    if ((result["latitude_deg"] < -90) | (result["latitude_deg"] > 90)).any():
        raise ValueError("latitude_deg must be within [-90, 90].")

    if ((result["longitude_deg"] < -180) | (result["longitude_deg"] > 360)).any():
        raise ValueError("longitude_deg must be within [-180, 360].")

    if (result["altitude_km"] < 0).any():
        raise ValueError("altitude_km must be >= 0.")

    def valid_values(
        frame: pd.DataFrame,
        *,
        label: str,
        cadence: str,
    ) -> pd.Series:
        if not isinstance(
            frame,
            pd.DataFrame,
        ):
            raise TypeError(f"{label} must be a pandas DataFrame.")

        required = {
            "timestamp",
            "value",
            "is_missing",
        }

        absent = required - set(frame.columns)

        if absent:
            raise ValueError(f"{label} is missing: " + ", ".join(sorted(absent)))

        valid = frame.loc[
            ~frame["is_missing"].astype(bool),
            [
                "timestamp",
                "value",
            ],
        ].copy()

        valid["timestamp"] = pd.to_datetime(
            valid["timestamp"],
            utc=True,
            errors="raise",
        )

        valid["value"] = pd.to_numeric(
            valid["value"],
            errors="raise",
        )

        if valid["value"].isna().any():
            raise ValueError(f"{label} contains missing valid values.")

        if cadence == "day":
            key = valid["timestamp"].dt.floor("D")

            if not (valid["timestamp"] == key).all():
                raise ValueError(f"{label} must use exact UTC day timestamps.")

        elif cadence == "3h":
            key = valid["timestamp"].dt.floor("3h")

            if not (valid["timestamp"] == key).all():
                raise ValueError(f"{label} must use exact UTC 3-hour timestamps.")

        else:
            raise ValueError("unsupported cadence.")

        if key.duplicated(keep=False).any():
            duplicate_keys = (
                key.loc[key.duplicated(keep=False)].astype(str).unique().tolist()
            )

            raise ValueError(
                f"{label} has multiple valid values for: " + ", ".join(duplicate_keys)
            )

        return pd.Series(
            valid["value"].to_numpy(),
            index=pd.DatetimeIndex(key),
            dtype="float64",
        ).sort_index()

    f107_values = valid_values(
        f107,
        label="F10.7",
        cadence="day",
    )

    ap_daily_values = valid_values(
        ap_daily,
        label="daily Ap",
        cadence="day",
    )

    ap_values = valid_values(
        ap_3h,
        label="3-hour Ap",
        cadence="3h",
    )

    trajectory_days = result["timestamp"].dt.floor("D")

    unique_days = trajectory_days.drop_duplicates().sort_values()

    f107_previous = {}
    f107a = {}
    daily_ap = {}

    for day in unique_days:
        previous_day = day - pd.Timedelta(days=1)

        centered = pd.date_range(
            day - pd.Timedelta(days=40),
            day + pd.Timedelta(days=40),
            freq="D",
        )

        required_f107 = centered.union(
            pd.DatetimeIndex(
                [
                    previous_day,
                ]
            )
        )

        missing_f107 = required_f107.difference(f107_values.index)

        if len(missing_f107):
            raise ValueError(
                "F10.7 is missing required "
                "UTC day(s): "
                + ", ".join(timestamp.isoformat() for timestamp in missing_f107)
            )

        if day not in (ap_daily_values.index):
            raise ValueError(f"daily Ap is missing required UTC day: {day.isoformat()}")

        f107_previous[day] = float(f107_values.loc[previous_day])

        f107a[day] = float(f107_values.loc[centered].mean())

        daily_ap[day] = float(ap_daily_values.loc[day])

    result["f107_previous_day_sfu"] = trajectory_days.map(f107_previous)

    result["f107a_81day_centered_sfu"] = trajectory_days.map(f107a)

    result["ap_daily"] = trajectory_days.map(daily_ap)

    ap_bins = result["timestamp"].dt.floor("3h")

    unique_bins = ap_bins.drop_duplicates().sort_values()

    vectors = {}

    def exact_ap(
        timestamp: pd.Timestamp,
    ) -> float:
        if timestamp not in (ap_values.index):
            raise ValueError(
                f"3-hour Ap is missing required timestamp: {timestamp.isoformat()}"
            )

        return float(ap_values.loc[timestamp])

    for current in unique_bins:
        avg_12_33 = [
            exact_ap(current - pd.Timedelta(hours=hours))
            for hours in range(
                12,
                34,
                3,
            )
        ]

        avg_36_57 = [
            exact_ap(current - pd.Timedelta(hours=hours))
            for hours in range(
                36,
                58,
                3,
            )
        ]

        vectors[current] = {
            "ap_current_3h": exact_ap(current),
            "ap_3h_prior": exact_ap(current - pd.Timedelta(hours=3)),
            "ap_6h_prior": exact_ap(current - pd.Timedelta(hours=6)),
            "ap_9h_prior": exact_ap(current - pd.Timedelta(hours=9)),
            "ap_12_33h_avg": sum(avg_12_33) / 8.0,
            "ap_36_57h_avg": sum(avg_36_57) / 8.0,
        }

    ap_frame = (
        pd.DataFrame.from_dict(
            vectors,
            orient="index",
        )
        .rename_axis("_ap_bin")
        .reset_index()
    )

    result["_ap_bin"] = ap_bins

    result = result.merge(
        ap_frame,
        on="_ap_bin",
        how="left",
        validate="many_to_one",
        sort=False,
    ).drop(
        columns=[
            "_ap_bin",
        ]
    )

    if result[list(MSIS_INPUT_COLUMNS)].isna().any().any():
        raise RuntimeError("MSIS forcing construction produced missing values.")

    return result.loc[
        :,
        list(MSIS_INPUT_COLUMNS),
    ]


def _load_pymsis():
    try:
        import pymsis
    except ImportError as exc:
        raise RuntimeError(
            "MSIS modeling requires the Orbitoby "
            "'models' extra. Install with "
            "`pip install orbitoby[models]`."
        ) from exc

    return pymsis


def _prepare_inputs(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    if not isinstance(
        frame,
        pd.DataFrame,
    ):
        raise TypeError("inputs must be a pandas DataFrame.")

    if frame.empty:
        raise ValueError("MSIS inputs must not be empty.")

    missing = set(MSIS_INPUT_COLUMNS) - set(frame.columns)

    if missing:
        raise ValueError("MSIS input frame is missing: " + ", ".join(sorted(missing)))

    result = frame.loc[
        :,
        list(MSIS_INPUT_COLUMNS),
    ].copy()

    result["timestamp"] = pd.to_datetime(
        result["timestamp"],
        utc=True,
        errors="raise",
    )

    numeric_columns = [column for column in MSIS_INPUT_COLUMNS if column != "timestamp"]

    for column in numeric_columns:
        result[column] = pd.to_numeric(
            result[column],
            errors="raise",
        )

        if result[column].isna().any():
            raise ValueError(f"{column} contains missing values.")

    if ((result["latitude_deg"] < -90) | (result["latitude_deg"] > 90)).any():
        raise ValueError("latitude_deg must be within [-90, 90].")

    if ((result["longitude_deg"] < -180) | (result["longitude_deg"] > 360)).any():
        raise ValueError("longitude_deg must be within [-180, 360].")

    if (result["altitude_km"] < 0).any():
        raise ValueError("altitude_km must be >= 0.")

    ap_columns = [column for column in MSIS_INPUT_COLUMNS if column.startswith("ap_")]

    for column in ap_columns:
        if (result[column] < 0).any():
            raise ValueError(f"{column} must be >= 0.")

    return result


def calculate_msis_density(
    inputs: pd.DataFrame,
    *,
    geomagnetic_activity: int = -1,
    backend: Any | None = None,
) -> MSISRun:
    """
    Calculate NRLMSIS 2.1 neutral total mass density.

    All solar/geomagnetic forcing must be supplied
    explicitly. Orbitoby never permits pymsis to
    auto-download or infer F10.7/Ap inputs here.
    """

    if geomagnetic_activity not in {
        -1,
        1,
    }:
        raise ValueError(
            "geomagnetic_activity must be -1 (storm-time Ap) or 1 (daily Ap)."
        )

    frame = _prepare_inputs(inputs)

    pymsis = backend if backend is not None else _load_pymsis()

    timestamps = (
        frame["timestamp"]
        .dt.tz_convert("UTC")
        .dt.tz_localize(None)
        .to_numpy(dtype="datetime64[ns]")
    )

    aps = frame[
        [
            "ap_daily",
            "ap_current_3h",
            "ap_3h_prior",
            "ap_6h_prior",
            "ap_9h_prior",
            "ap_12_33h_avg",
            "ap_36_57h_avg",
        ]
    ].to_numpy()

    output = pymsis.calculate(
        timestamps,
        frame["longitude_deg"].to_numpy(),
        frame["latitude_deg"].to_numpy(),
        frame["altitude_km"].to_numpy(),
        f107s=frame["f107_previous_day_sfu"].to_numpy(),
        f107as=frame["f107a_81day_centered_sfu"].to_numpy(),
        aps=aps,
        version=2.1,
        geomagnetic_activity=(geomagnetic_activity),
        interpolate_indices=False,
    )

    mass_index = int(pymsis.Variable.MASS_DENSITY)

    densities = output[
        ...,
        mass_index,
    ]

    # Aligned fly-through input should produce
    # one density value per input timestamp.
    densities = densities.reshape(-1)

    if len(densities) != len(frame):
        raise RuntimeError("pymsis returned an unexpected output shape.")

    values = pd.Series(
        densities,
        dtype="Float64",
    )

    result = pd.DataFrame(
        {
            "timestamp": frame["timestamp"],
            "value": values,
            "is_missing": (values.isna()),
            "missing_reason": [
                ("model_missing" if missing else None) for missing in values.isna()
            ],
            "interval_start": pd.NaT,
            "interval_end": pd.NaT,
            "context": [
                {
                    "longitude_deg": row.longitude_deg,
                    "latitude_deg": row.latitude_deg,
                    "altitude_km": row.altitude_km,
                    "f107_previous_day_sfu": (row.f107_previous_day_sfu),
                    "f107a_81day_centered_sfu": (row.f107a_81day_centered_sfu),
                    "ap": [
                        row.ap_daily,
                        row.ap_current_3h,
                        row.ap_3h_prior,
                        row.ap_6h_prior,
                        row.ap_9h_prior,
                        row.ap_12_33h_avg,
                        row.ap_36_57h_avg,
                    ],
                    "geomagnetic_activity": (geomagnetic_activity),
                    "interpolate_indices": False,
                }
                for row in frame.itertuples(index=False)
            ],
        }
    )

    try:
        backend_version = version("pymsis")
    except PackageNotFoundError:
        backend_version = getattr(
            pymsis,
            "__version__",
            "unknown",
        )

    return MSISRun(
        data=result,
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        backend="pymsis",
        backend_version=str(backend_version),
        geomagnetic_activity=(geomagnetic_activity),
        interpolate_indices=False,
    )
