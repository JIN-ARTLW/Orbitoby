from types import SimpleNamespace

import pandas as pd
import pytest

from orbitoby._easy import Study
from orbitoby._easy_result import DataResult


def make_orbit(epochs, values):
    frame = pd.DataFrame(
        {
            "epoch": epochs,
            "mean_motion": values,
            "norad_id": [22] * len(epochs),
            "source": ["spacetrack"] * len(epochs),
        }
    )

    core = SimpleNamespace(
        orbit=lambda **kwargs: frame,
    )

    study = SimpleNamespace(
        _core=core,
        start="2000-01-01",
        end="2000-01-10",
    )

    return Study.orbit(
        study,
        22,
        sync=False,
    )


def test_core_naive_orbit_epoch_becomes_utc():
    result = make_orbit(
        ["2000-01-01 00:00:00", "2000-01-02 00:00:00"],
        [14.1, 14.2],
    )

    epochs = result.table["epoch"]

    assert isinstance(epochs.dtype, pd.DatetimeTZDtype)
    assert str(epochs.dt.tz) == "UTC"

    changed = result.change("mean_motion")

    assert len(changed.table) == 1
    assert changed.table["value"].iloc[0] == pytest.approx(0.1)
    assert changed.table["interval_seconds"].iloc[0] == 86400


def test_duplicate_orbit_epochs_are_not_silently_discarded():
    result = make_orbit(
        [
            "2000-01-01 00:00:00",
            "2000-01-01 00:00:00",
            "2000-01-02 00:00:00",
        ],
        [14.1, 14.15, 14.2],
    )

    assert len(result.table) == 3

    with pytest.raises(ValueError, match="Duplicate epochs"):
        result.change("mean_motion")


def test_arbitrary_naive_data_still_rejected():
    result = DataResult(
        pd.DataFrame(
            {
                "timestamp": [
                    "2000-01-01 00:00:00",
                    "2000-01-02 00:00:00",
                ],
                "value": [1.0, 2.0],
            }
        ),
        name="general data",
        start="2000-01-01",
        end="2000-01-03",
        source="untrusted",
    )

    with pytest.raises(TypeError, match="timezone-aware"):
        result.change()
