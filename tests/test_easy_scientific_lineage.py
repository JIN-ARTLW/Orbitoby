from types import SimpleNamespace

import duckdb
import pandas as pd

from orbitoby._easy import Study
from orbitoby._easy_lineage import verified_scientific_artifact_ids
from orbitoby._easy_result import DataResult


def make_core():
    con = duckdb.connect(":memory:")

    con.execute("""
        CREATE TABLE artifacts (
            artifact_id VARCHAR,
            source VARCHAR,
            dataset VARCHAR,
            sha256 VARCHAR
        )
    """)

    con.execute("""
        CREATE TABLE scientific_files (
            artifact_id VARCHAR,
            source VARCHAR,
            dataset VARCHAR,
            metric VARCHAR,
            raw_sha256 VARCHAR
        )
    """)

    con.execute("""
        INSERT INTO artifacts VALUES
        ('a1', 'gfz', 'f107_observed', 'hash1')
    """)

    con.execute("""
        INSERT INTO scientific_files VALUES
        ('a1', 'gfz', 'f107_observed', 'f107_observed', 'hash1')
    """)

    return con


def make_frame():
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2024-01-01", "2024-01-02"],
                utc=True,
            ),
            "metric": ["f107_observed", "f107_observed"],
            "value": [135.7, 142.1],
            "source": ["gfz", "gfz"],
            "dataset": ["f107_observed", "f107_observed"],
            "artifact_id": ["a1", "a1"],
        }
    )


def test_valid_scientific_lineage_is_verified():
    con = make_core()
    try:
        core = SimpleNamespace(con=con)
        assert verified_scientific_artifact_ids(core, make_frame()) == ("a1",)
    finally:
        con.close()


def test_wrong_provider_cannot_claim_artifact():
    con = make_core()
    try:
        frame = make_frame()
        frame["source"] = "other-provider"

        assert verified_scientific_artifact_ids(SimpleNamespace(con=con), frame) == ()
    finally:
        con.close()


def test_wrong_checksum_cannot_claim_artifact():
    con = make_core()
    try:
        con.execute("""
            UPDATE scientific_files
            SET raw_sha256 = 'incorrect'
        """)

        assert (
            verified_scientific_artifact_ids(SimpleNamespace(con=con), make_frame())
            == ()
        )
    finally:
        con.close()


def test_mixed_verified_and_unverified_rows_fail_closed():
    con = make_core()
    try:
        frame = make_frame()
        frame.loc[1, "artifact_id"] = "forged"

        assert verified_scientific_artifact_ids(SimpleNamespace(con=con), frame) == ()
    finally:
        con.close()


def test_plain_dataresult_does_not_trust_same_columns():
    frame = make_frame()

    result = DataResult(
        frame,
        name="untrusted",
        start="2024-01-01",
        end="2024-01-03",
        source="gfz",
    )

    assert result.provenance.empty


def test_study_weather_attests_core_result():
    con = make_core()

    try:
        core = SimpleNamespace(
            con=con,
            space_weather=lambda **kwargs: make_frame(),
        )

        study = SimpleNamespace(
            _core=core,
            start="2024-01-01",
            end="2024-01-03",
        )

        result = Study.weather(study, "f107")

        assert result.provenance["artifact_id"].tolist() == ["a1"]
        assert result.change().provenance["artifact_id"].tolist() == ["a1"]
    finally:
        con.close()
