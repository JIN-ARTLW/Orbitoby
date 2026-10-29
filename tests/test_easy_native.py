import pandas as pd
import pytest

import orbitoby as ob


class FakeArchive:
    def __init__(self):
        self.calls = []

    def sources_available(self):
        return ["gfz", "provider_two"]

    def datasets(self, *, source=None, live=False):
        assert not live

        records = [
            {
                "source": "gfz",
                "dataset": "kp",
                "canonical_metrics": ["kp"],
                "data_scope": "global",
            },
            {
                "source": "provider_two",
                "dataset": "kp",
                "canonical_metrics": ["kp"],
                "data_scope": "global",
            },
            {
                "source": "provider_two",
                "dataset": "object_list",
                "canonical_metrics": [],
                "data_scope": "object_catalogue",
            },
        ]

        if source:
            return [row for row in records if row["source"] == source]

        return records

    def fetch(self, **kwargs):
        self.calls.append(kwargs)

        if kwargs["dataset"] == "object_list":
            return pd.DataFrame(
                {
                    "object_id": [123],
                    "object_type": ["payload"],
                }
            )

        return pd.DataFrame(
            {
                "timestamp": ["2024-05-10T00:00:00Z"],
                "metric": ["kp"],
                "value": [2.667],
                "unit": ["1"],
                "source": [kwargs["source"]],
                "dataset": [kwargs["dataset"]],
                "context": [{"native": "preserved"}],
            }
        )


def make_study():
    study = ob.study("2024-05-10", "2024-05-11")
    study._archive = FakeArchive()
    return study


def test_explicit_dataset_and_period():
    study = make_study()

    result = study.data("kp", source="GFZ")

    assert result.table.loc[0, "value"] == 2.667
    assert result.table.loc[0, "context"] == {"native": "preserved"}

    call = study._archive.calls[0]

    assert call["source"] == "gfz"
    assert call["dataset"] == "kp"
    assert call["archive_raw"] is True
    assert call["start"] == study.start
    assert call["end"] == study.end


def test_ambiguous_dataset_rejected_before_fetch():
    study = make_study()

    with pytest.raises(ValueError, match="ambiguous"):
        study.data("kp")

    assert study._archive.calls == []


def test_non_timeseries_is_not_falsely_plotted():
    study = make_study()

    result = study.data("object_list", source="provider_two")

    assert "start" not in study._archive.calls[0]
    assert "end" not in study._archive.calls[0]

    with pytest.raises(ValueError, match="not a declared scalar"):
        result.plot()


@pytest.mark.parametrize(
    "keyword",
    ["access_token", "password", "api_key", "authorization"],
)
def test_credentials_never_forwarded_to_core(keyword):
    study = make_study()

    with pytest.raises(ValueError, match="credentials"):
        study.data("kp", source="gfz", **{keyword: "secret"})

    assert not study._archive.calls


def test_normalized_data_has_safe_shared_export(tmp_path):
    study = make_study()
    result = study.data("kp", source="gfz")

    path = result.save(tmp_path / "kp.csv")

    saved = path.read_text()

    assert "2.667" in saved
    assert "context" not in saved
    assert (tmp_path / "kp_export.json").exists()


@pytest.mark.parametrize(
    "invalid",
    [
        {"nested": "value"},
        b"binary-content",
        [["nested", "list"]],
    ],
)
def test_native_options_reject_nested_and_binary_values(invalid):
    study = make_study()

    with pytest.raises(TypeError, match="Nested or binary"):
        study.data(
            "kp",
            source="gfz",
            unsupported=invalid,
        )

    assert not study._archive.calls
