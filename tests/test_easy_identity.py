import json

import pandas as pd
import pytest

import orbitoby as ob


class FakeArchive:
    def __init__(self):
        self.calls = []

    def object(self, **kwargs):
        self.calls.append(("object", kwargs))

        if kwargs.get("norad_id") == 99999:
            return None

        return {
            "object_id": "object-1",
            "norad_id": 39452,
            "name": "Swarm A",
            "identifiers": [{"namespace": "norad", "identifier": "39452"}],
            "source_records": [
                {
                    "record_id": "record-1",
                    "artifact_id": "artifact-1",
                    "source": "celestrak",
                    "dataset": "satcat",
                    "data": {"native_property": "preserved"},
                }
            ],
            "properties": [{"property": "mass", "value": 450}],
        }

    def search(self, **kwargs):
        self.calls.append(("search", kwargs))

        return pd.DataFrame(
            {
                "object_id": ["object-1"],
                "norad_id": [39452],
                "name": ["Swarm A"],
            }
        )


def study_with_archive():
    study = ob.study("2024-05-10", "2024-05-20")
    study._archive = FakeArchive()
    return study


def test_object_preserves_core_identity():
    study = study_with_archive()

    result = study.object(39452)

    assert result.table.loc[0, "norad_id"] == 39452
    assert result.details["source_records"][0]["data"] == {
        "native_property": "preserved"
    }
    assert len(result.records()) == 1

    assert study._archive.calls[0] == (
        "object",
        {
            "norad_id": 39452,
            "cospar_id": None,
            "object_id": None,
        },
    )


def test_object_details_are_defensively_copied():
    result = study_with_archive().object(39452)

    copy = result.details
    copy["source_records"][0]["data"]["native_property"] = "changed"

    assert result.details["source_records"][0]["data"]["native_property"] == "preserved"


def test_missing_local_object_not_claimed_absent_from_space():
    study = study_with_archive()

    with pytest.raises(LookupError, match="local index"):
        study.object(99999)


def test_search_preserves_core_filters():
    study = study_with_archive()

    result = study.search(
        "Swarm",
        source="celestrak",
        limit=20,
    )

    assert result.table.loc[0, "norad_id"] == 39452

    kind, params = study._archive.calls[0]

    assert kind == "search"
    assert params["name"] == "Swarm"
    assert params["source"] == "celestrak"
    assert params["limit"] == 20


def test_search_is_not_misrepresented_as_period_filtered(capsys):
    result = study_with_archive().search("Swarm")

    result.info()
    output = capsys.readouterr().out

    assert "all locally indexed records" in output
    assert "Study dates do not filter" in output


def test_archive_wide_export_explains_time_scope(tmp_path):
    result = study_with_archive().search("Swarm")

    result.save(tmp_path / "search.csv")

    metadata = json.loads((tmp_path / "search_export.json").read_text())

    assert "archive-wide" in metadata["time_convention"]


def test_object_public_csv_does_not_export_nested_records(tmp_path):
    result = study_with_archive().object(39452)

    path = result.save(tmp_path / "object.csv")

    assert "native_property" not in path.read_text()
    assert "39452" in path.read_text()
    assert "source_records" not in path.read_text()


@pytest.mark.parametrize("invalid", [0, -1, True, "39452"])
def test_invalid_positional_norad_id(invalid):
    study = study_with_archive()

    with pytest.raises(ValueError, match="positive NORAD"):
        study.object(invalid)
