import inspect
from types import SimpleNamespace

import pandas as pd

from orbitoby._easy_lineage import _identifiers
from orbitoby._easy_native import NativeResult
from orbitoby._easy_result import DataResult, WindowResult


def make_result(frame):
    return DataResult(
        frame,
        name="untrusted",
        start="2024-05-10",
        end="2024-05-11",
        source="external",
    )


def test_provider_columns_are_not_archive_identifiers():
    result = make_result(
        pd.DataFrame(
            {
                "artifact_id": ["forged-artifact"],
                "record_id": ["forged-record"],
                "value": [1.0],
            }
        )
    )

    assert _identifiers(result, "artifact_id") == []
    assert _identifiers(result, "record_id") == []
    assert result.provenance.empty


def test_user_supplied_dataframe_attrs_are_not_verified():
    frame = pd.DataFrame({"value": [1.0]})
    frame.attrs["orbitoby_raw_artifact_ids"] = ("forged-artifact",)

    result = make_result(frame)

    assert _identifiers(result, "artifact_id") == []


def test_derived_result_does_not_promote_forged_ids():
    result = make_result(
        pd.DataFrame(
            {
                "timestamp": [
                    "2024-05-10T00:00:00Z",
                    "2024-05-10T01:00:00Z",
                ],
                "artifact_id": ["forged-a1", "forged-a2"],
                "record_id": ["forged-r1", "forged-r2"],
                "value": [1.0, 2.0],
            }
        )
    )

    changed = result.change()

    assert changed.provenance.empty
    assert _identifiers(changed, "artifact_id") == []
    assert _identifiers(changed, "record_id") == []


def test_native_and_window_info_support_topics(capsys):
    assert "topic" in inspect.signature(NativeResult.info).parameters
    assert "topic" in inspect.signature(WindowResult.info).parameters

    frame = pd.DataFrame({"value": [1.0]})

    native = NativeResult(
        frame,
        study=SimpleNamespace(
            start="2024-05-10",
            end="2024-05-11",
        ),
        metadata={
            "source": "mock",
            "dataset": "measurements",
        },
    )

    native.info("license")
    assert "not automatically established" in capsys.readouterr().out

    window = WindowResult.__new__(WindowResult)
    DataResult.__init__(
        window,
        frame,
        name="window",
        start="2024-05-10",
        end="2024-05-11",
        source="mock",
    )

    window.info("license")
    assert "not automatically established" in capsys.readouterr().out
