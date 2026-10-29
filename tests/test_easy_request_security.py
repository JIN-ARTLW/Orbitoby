from types import SimpleNamespace

from orbitoby._easy_lineage import _identifiers
from orbitoby._easy_native import fetch_data
from orbitoby.service import Archive


def make_archive(monkeypatch):
    captured = {}

    def save_raw_artifact(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(artifact_id="verified-artifact")

    monkeypatch.setattr(
        "orbitoby.service.save_raw_artifact",
        save_raw_artifact,
    )

    adapter = SimpleNamespace(
        fetch=lambda dataset, **params: b'{"value": 12}',
        normalize=lambda dataset, payload, **params: [
            {
                "artifact_id": "provider-forged-id",
                "record_id": "provider-forged-record",
                "value": 12.0,
            }
        ],
        raw_extension_for=lambda dataset, **params: "json",
        should_index_identity_request=lambda dataset, **params: False,
    )

    archive = Archive.__new__(Archive)
    archive.get_source = lambda source: adapter
    archive._register_artifact = lambda artifact: None
    archive.sources_available = lambda: ["mock"]
    archive.datasets = lambda source=None, live=False: [
        {
            "source": "mock",
            "dataset": "measurements",
            "data_scope": "global",
        }
    ]

    return archive, captured


def test_private_parameters_never_enter_raw_request_metadata(monkeypatch):
    archive, captured = make_archive(monkeypatch)

    frame = archive.fetch(
        source="mock",
        dataset="measurements",
        start="2024-05-10",
        end="2024-05-11",
        norad_id=39452,
        token="PRIVATE_TOKEN",
        password="PRIVATE_PASSWORD",
        url="https://user:secret@example.org/api",
    )

    metadata = captured["metadata"]
    serialized = repr(metadata)

    assert "PRIVATE_TOKEN" not in serialized
    assert "PRIVATE_PASSWORD" not in serialized
    assert "user:secret" not in serialized
    assert "token" not in serialized
    assert "password" not in serialized

    assert metadata["params"]["norad_id"] == 39452
    assert metadata["params"]["start"] == "2024-05-10"
    assert metadata["additional_options_omitted"] is True
    assert frame.attrs["orbitoby_raw_artifact_ids"] == ("verified-artifact",)


def test_study_native_path_preserves_verified_core_artifact(monkeypatch):
    archive, _ = make_archive(monkeypatch)

    study = SimpleNamespace(
        _core=archive,
        start="2024-05-10",
        end="2024-05-11",
    )

    result = fetch_data(
        study,
        "measurements",
        source="mock",
    )

    assert result.table["value"].tolist() == [12.0]
    assert _identifiers(result, "artifact_id") == ["verified-artifact"]
    assert _identifiers(result, "record_id") == []
    assert result.provenance["artifact_id"].tolist() == ["verified-artifact"]
