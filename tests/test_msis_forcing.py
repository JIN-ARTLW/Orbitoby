import pandas as pd
import pytest

from orbitoby.models.msis import (
    MSIS_INPUT_COLUMNS,
    build_msis_inputs,
)

DAY = pd.Timestamp("2024-01-01T00:00:00Z")


def trajectory():
    return pd.DataFrame(
        {
            "timestamp": [
                DAY,
                DAY + pd.Timedelta(hours=3),
            ],
            "longitude_deg": [
                100.0,
                110.0,
            ],
            "latitude_deg": [
                -10.0,
                20.0,
            ],
            "altitude_km": [
                480.0,
                482.0,
            ],
        }
    )


def canonical(
    timestamps,
    values,
):
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "value": values,
            "is_missing": False,
        }
    )


def drivers():
    f107_times = pd.date_range(
        DAY - pd.Timedelta(days=40),
        DAY + pd.Timedelta(days=40),
        freq="D",
    )

    f107 = canonical(
        f107_times,
        [100.0 + index for index in range(len(f107_times))],
    )

    ap_daily = canonical(
        [
            DAY,
        ],
        [
            10.0,
        ],
    )

    ap_times = pd.date_range(
        DAY - pd.Timedelta(hours=57),
        DAY + pd.Timedelta(hours=3),
        freq="3h",
    )

    ap_3h = canonical(
        ap_times,
        [float(index + 1) for index in range(len(ap_times))],
    )

    return (
        f107,
        ap_daily,
        ap_3h,
    )


def test_build_msis_inputs_exact_forcing():
    f107, ap_daily, ap_3h = drivers()

    result = build_msis_inputs(
        trajectory(),
        f107=f107,
        ap_daily=ap_daily,
        ap_3h=ap_3h,
    )

    assert tuple(result.columns) == MSIS_INPUT_COLUMNS

    assert len(result) == 2

    # DAY - 1 is index 39 in the
    # centered 81-day sequence.
    assert (
        result.loc[
            0,
            "f107_previous_day_sfu",
        ]
        == 139.0
    )

    # Arithmetic mean of 100..180.
    assert (
        result.loc[
            0,
            "f107a_81day_centered_sfu",
        ]
        == 140.0
    )

    assert (
        result.loc[
            0,
            "ap_daily",
        ]
        == 10.0
    )

    # DAY is the 20th timestamp in
    # the -57 h ... sequence.
    assert (
        result.loc[
            0,
            "ap_current_3h",
        ]
        == 20.0
    )

    assert (
        result.loc[
            0,
            "ap_3h_prior",
        ]
        == 19.0
    )

    assert (
        result.loc[
            0,
            "ap_6h_prior",
        ]
        == 18.0
    )

    assert (
        result.loc[
            0,
            "ap_9h_prior",
        ]
        == 17.0
    )


def test_build_msis_inputs_rejects_missing_f107_day():
    f107, ap_daily, ap_3h = drivers()

    f107 = f107.iloc[1:].reset_index(drop=True)

    with pytest.raises(
        ValueError,
        match="F10.7 is missing",
    ):
        build_msis_inputs(
            trajectory(),
            f107=f107,
            ap_daily=ap_daily,
            ap_3h=ap_3h,
        )


def test_build_msis_inputs_rejects_missing_ap_bin():
    f107, ap_daily, ap_3h = drivers()

    missing_time = DAY - pd.Timedelta(hours=9)

    ap_3h = ap_3h.loc[
        pd.to_datetime(
            ap_3h["timestamp"],
            utc=True,
        )
        != missing_time
    ].reset_index(drop=True)

    with pytest.raises(
        ValueError,
        match="3-hour Ap is missing",
    ):
        build_msis_inputs(
            trajectory(),
            f107=f107,
            ap_daily=ap_daily,
            ap_3h=ap_3h,
        )


def test_build_msis_inputs_rejects_duplicate_trajectory_time():
    f107, ap_daily, ap_3h = drivers()

    data = trajectory()

    data.loc[
        1,
        "timestamp",
    ] = data.loc[
        0,
        "timestamp",
    ]

    with pytest.raises(
        ValueError,
        match="duplicate timestamps",
    ):
        build_msis_inputs(
            data,
            f107=f107,
            ap_daily=ap_daily,
            ap_3h=ap_3h,
        )


def test_archive_forcing_rejects_duplicate_driver_claims():
    from orbitoby import Archive, ProductParent

    f107, daily, three_hour = drivers()
    frames = {
        "f107_observed": pd.concat([f107, f107.iloc[[0]]]),
        "ap_daily": daily,
        "ap": three_hour,
    }
    archive = Archive.__new__(Archive)

    def series(metric, **kwargs):
        assert kwargs["artifact_resolution"] == "all"
        return frames[metric].assign(artifact_id="raw-test")

    archive.timeseries = series
    with pytest.raises(ValueError, match="multiple valid values"):
        archive.msis_inputs(
            trajectory(),
            driver_source="gfz",
            trajectory_parents=[
                ProductParent("raw_artifact", "trajectory", "trajectory_input")
            ],
        )


def test_archive_forcing_requires_provenance_on_every_driver_row():
    from orbitoby import Archive, ProductParent

    f107, daily, three_hour = drivers()
    frames = {"f107_observed": f107, "ap_daily": daily, "ap": three_hour}
    archive = Archive.__new__(Archive)

    def series(metric, **kwargs):
        frame = frames[metric].assign(artifact_id="raw-test")
        frame.loc[0, "artifact_id"] = None
        return frame

    archive.timeseries = series
    with pytest.raises(ValueError, match="without artifact provenance"):
        archive.msis_inputs(
            trajectory(),
            driver_source="gfz",
            trajectory_parents=[
                ProductParent("raw_artifact", "trajectory", "trajectory_input")
            ],
        )
