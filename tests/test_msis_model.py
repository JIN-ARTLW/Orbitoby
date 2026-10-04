from enum import IntEnum

import pandas as pd
import pytest

from orbitoby.models.msis import (
    calculate_msis_density,
)


class Variable(IntEnum):
    MASS_DENSITY = 0


class FakeMSIS:
    Variable = Variable
    __version__ = "test"

    def __init__(self):
        self.calls = []

    def calculate(
        self,
        dates,
        lons,
        lats,
        alts,
        *,
        f107s,
        f107as,
        aps,
        version,
        geomagnetic_activity,
        interpolate_indices,
    ):
        self.calls.append(
            {
                "dates": dates,
                "lons": lons,
                "lats": lats,
                "alts": alts,
                "f107s": f107s,
                "f107as": f107as,
                "aps": aps,
                "version": version,
                "geomagnetic_activity": (geomagnetic_activity),
                "interpolate_indices": (interpolate_indices),
            }
        )

        import numpy as np

        result = np.zeros(
            (
                len(dates),
                11,
            )
        )

        result[:, 0] = [
            1.2e-12,
            1.4e-12,
        ]

        return result


def inputs():
    return pd.DataFrame(
        {
            "timestamp": [
                "2024-05-10T00:00:00Z",
                "2024-05-10T03:00:00Z",
            ],
            "longitude_deg": [
                127.0,
                127.1,
            ],
            "latitude_deg": [
                37.0,
                37.1,
            ],
            "altitude_km": [
                400.0,
                401.0,
            ],
            "f107_previous_day_sfu": [
                180.0,
                180.0,
            ],
            "f107a_81day_centered_sfu": [
                160.0,
                160.0,
            ],
            "ap_daily": [
                20.0,
                20.0,
            ],
            "ap_current_3h": [
                40.0,
                50.0,
            ],
            "ap_3h_prior": [
                30.0,
                40.0,
            ],
            "ap_6h_prior": [
                20.0,
                30.0,
            ],
            "ap_9h_prior": [
                15.0,
                20.0,
            ],
            "ap_12_33h_avg": [
                10.0,
                10.0,
            ],
            "ap_36_57h_avg": [
                8.0,
                8.0,
            ],
        }
    )


def test_msis_uses_explicit_forcing():
    backend = FakeMSIS()

    result = calculate_msis_density(
        inputs(),
        backend=backend,
    )

    call = backend.calls[0]

    assert call["version"] == 2.1

    assert call["geomagnetic_activity"] == -1

    assert call["interpolate_indices"] is False

    assert list(call["f107s"]) == [
        180.0,
        180.0,
    ]

    assert call["aps"].shape == (
        2,
        7,
    )

    assert len(result.data) == 2


def test_msis_output_is_model_density():
    result = calculate_msis_density(
        inputs(),
        backend=FakeMSIS(),
    )

    assert result.model_name == ("NRLMSIS")

    assert result.model_version == ("2.1")

    assert result.data["value"].tolist() == [
        1.2e-12,
        1.4e-12,
    ]

    assert not result.data["is_missing"].any()


def test_msis_context_preserves_inputs():
    result = calculate_msis_density(
        inputs(),
        backend=FakeMSIS(),
    )

    context = result.data.loc[
        0,
        "context",
    ]

    assert context["altitude_km"] == 400.0

    assert context["f107_previous_day_sfu"] == 180.0

    assert len(context["ap"]) == 7

    assert context["interpolate_indices"] is False


def test_msis_rejects_missing_forcing():
    data = inputs().drop(columns=["f107a_81day_centered_sfu"])

    with pytest.raises(
        ValueError,
        match="f107a",
    ):
        calculate_msis_density(
            data,
            backend=FakeMSIS(),
        )


def test_msis_rejects_invalid_latitude():
    data = inputs()

    data.loc[
        0,
        "latitude_deg",
    ] = 91.0

    with pytest.raises(
        ValueError,
        match="latitude",
    ):
        calculate_msis_density(
            data,
            backend=FakeMSIS(),
        )


def test_msis_rejects_implicit_activity_mode():
    with pytest.raises(
        ValueError,
        match="geomagnetic_activity",
    ):
        calculate_msis_density(
            inputs(),
            geomagnetic_activity=0,
            backend=FakeMSIS(),
        )
