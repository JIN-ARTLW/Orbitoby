from types import SimpleNamespace

import pandas as pd

from orbitoby._easy_lineage import _identifiers
from orbitoby._easy_native import NativeResult
from orbitoby.service import Archive


def fake_core_fetch(records, artifact_id):
    archive = Archive.__new__(Archive)
    artifact = (
        SimpleNamespace(artifact_id=artifact_id) if artifact_id is not None else None
    )
    archive._fetch_records = lambda **kwargs: (records, artifact)
    return archive.fetch(source="mock", dataset="native")


def native_result(frame):
    study = SimpleNamespace(
        start="2024-05-10",
        end="2024-05-20",
    )
    return NativeResult(
        frame,
        study=study,
        metadata={
            "source": "mock",
            "dataset": "native",
        },
    )


def test_core_fetch_preserves_actual_artifact_id():
    frame = fake_core_fetch(
        [{"native_value": 12.0}],
        "verified-a1",
    )

    assert frame["native_value"].tolist() == [12.0]
    assert frame.attrs["orbitoby_raw_artifact_ids"] == ("verified-a1",)


def test_native_result_retains_verified_raw_lineage():
    frame = fake_core_fetch(
        [{"native_value": 12.0}],
        "verified-a1",
    )
    result = native_result(frame)

    assert _identifiers(result, "artifact_id") == ["verified-a1"]
    assert result.provenance["artifact_id"].tolist() == ["verified-a1"]


def test_provider_native_ids_are_not_trusted():
    frame = fake_core_fetch(
        [
            {
                "artifact_id": "provider-spoofed",
                "record_id": "provider-record",
                "value": 12.0,
            }
        ],
        "verified-a1",
    )
    result = native_result(frame)

    assert _identifiers(result, "artifact_id") == ["verified-a1"]
    assert _identifiers(result, "record_id") == []


def test_no_archived_artifact_does_not_invent_lineage():
    frame = fake_core_fetch(
        [{"artifact_id": "provider-spoofed"}],
        None,
    )
    result = native_result(frame)

    assert _identifiers(result, "artifact_id") == []
    assert isinstance(result.provenance, pd.DataFrame)
    assert result.provenance.empty
