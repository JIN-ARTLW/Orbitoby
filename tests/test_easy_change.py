import pandas as pd
import pytest

from orbitoby._easy_result import DataResult


def example(**extra):
    values = {
        "timestamp": [
            "2024-05-10T00:00:00Z",
            "2024-05-10T01:00:00Z",
            "2024-05-10T04:00:00Z",
        ],
        "value": [10.0, 14.0, 20.0],
        "unit": ["km", "km", "km"],
    }
    values.update(extra)

    return DataResult(
        pd.DataFrame(values),
        name="measured quantity",
        start="2024-05-10",
        end="2024-05-11",
        source="test-provider",
    )


def test_difference_uses_only_observed_pairs():
    changed = example().change()

    assert changed.table["value"].tolist() == [4.0, 6.0]
    assert changed.table["data_role"].eq("orbitoby_derived").all()
    assert changed.table["unit"].eq("km").all()


def test_rate_uses_real_elapsed_seconds():
    changed = example().change(method="rate")

    assert changed.table["value"].tolist() == pytest.approx(
        [4.0 / 3600.0, 6.0 / 10800.0]
    )
    assert changed.table["unit"].eq("km/s").all()
    assert changed.table["interval_seconds"].tolist() == [
        3600.0,
        10800.0,
    ]


def test_missing_value_does_not_bridge_gap():
    changed = example(value=[10.0, None, 20.0]).change()
    assert changed.table.empty


def test_duplicate_timestamp_is_rejected():
    result = example(
        timestamp=[
            "2024-05-10T00:00:00Z",
            "2024-05-10T00:00:00Z",
            "2024-05-10T04:00:00Z",
        ],
    )

    with pytest.raises(ValueError, match="Duplicate"):
        result.change()


def test_naive_timestamp_is_rejected():
    result = example(
        timestamp=[
            "2024-05-10 00:00",
            "2024-05-10 01:00",
            "2024-05-10 04:00",
        ],
    )

    with pytest.raises(TypeError, match="timezone-aware"):
        result.change()


def test_change_only_exposes_verified_parent_artifacts():
    result = example(
        artifact_id=["a1", "a2", "a3"],
        record_id=["r1", "r2", "r3"],
    )

    assert result.provenance.empty
    assert result.change(method="rate").provenance.empty

    result._raw_artifact_ids = ("verified-a1",)
    changed = result.change(method="rate")

    assert changed.provenance["artifact_id"].tolist() == ["verified-a1"]
    assert "record_id" not in changed.provenance.columns


def test_info_topic_shows_coverage(capsys):
    result = example()

    result.info("coverage")

    assert "returned-result" in capsys.readouterr().out


def test_info_license_does_not_invent_permissions(capsys):
    example().info("license")

    assert "not automatically established" in capsys.readouterr().out


def test_info_topic_rejects_unknown():
    with pytest.raises(ValueError, match="Unknown info topic"):
        example().info("not-a-topic")
