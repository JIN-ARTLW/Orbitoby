from types import SimpleNamespace

import duckdb
import pandas as pd
import pytest

from orbitoby._easy import Study


@pytest.fixture
def orbital_archive():
    con = duckdb.connect(":memory:")

    con.execute("""
        CREATE TABLE artifacts (
            artifact_id VARCHAR,
            source VARCHAR,
            sha256 VARCHAR
        )
    """)

    con.execute("""
        CREATE TABLE orbit_elements (
            gp_id INTEGER,
            norad_id INTEGER,
            epoch TIMESTAMP,
            source VARCHAR,
            artifact_id VARCHAR,
            mean_motion DOUBLE
        )
    """)

    con.execute("""
        INSERT INTO artifacts VALUES
        ('a1', 'spacetrack', 'stored-checksum')
    """)

    con.execute("""
        INSERT INTO orbit_elements VALUES
        (101, 22, TIMESTAMP '2019-11-01 00:00:00',
         'spacetrack', 'a1', 14.1),
        (102, 22, TIMESTAMP '2019-11-02 00:00:00',
         'spacetrack', 'a1', 14.2)
    """)

    frame = pd.DataFrame(
        {
            "gp_id": [101, 102],
            "norad_id": [22, 22],
            "epoch": pd.to_datetime(
                [
                    "2019-11-01 00:00:00",
                    "2019-11-02 00:00:00",
                ]
            ),
            "source": ["spacetrack", "spacetrack"],
            "artifact_id": ["a1", "a1"],
            "mean_motion": [14.1, 14.2],
        }
    )

    yield con, frame

    con.close()


def orbit_result(con, frame):
    core = SimpleNamespace(
        con=con,
        orbit=lambda **kwargs: frame.copy(deep=True),
    )

    study = SimpleNamespace(
        _core=core,
        start="2019-11-01",
        end="2019-11-04",
    )

    return Study.orbit(study, 22, sync=False)


def test_realistic_lineage_survives_change(orbital_archive):
    con, frame = orbital_archive
    orbit = orbit_result(con, frame)

    assert orbit._raw_artifact_ids == ("a1",)
    assert orbit.provenance["artifact_id"].tolist() == ["a1"]

    changed = orbit.change("mean_motion")

    assert len(changed.table) == 1
    assert changed.table["value"].iloc[0] == pytest.approx(0.1)
    assert changed.provenance["artifact_id"].tolist() == ["a1"]


@pytest.mark.parametrize(
    ("field", "forged_value"),
    [
        ("gp_id", 999),
        ("norad_id", 23),
        ("epoch", pd.Timestamp("2019-11-03")),
        ("source", "other"),
        ("artifact_id", "forged-artifact"),
        ("mean_motion", 99.9),
    ],
)
def test_modified_orbit_record_fails_closed(orbital_archive, field, forged_value):
    con, frame = orbital_archive
    frame.loc[0, field] = forged_value

    result = orbit_result(con, frame)

    assert result._raw_artifact_ids == ()
    assert result.provenance.empty


def test_missing_checksum_fails_closed(orbital_archive):
    con, frame = orbital_archive

    con.execute("""
        UPDATE artifacts
        SET sha256 = NULL
        WHERE artifact_id = 'a1'
    """)

    result = orbit_result(con, frame)

    assert result.provenance.empty


def test_one_unverified_row_invalidates_entire_result(
    orbital_archive,
):
    con, frame = orbital_archive
    frame.loc[1, "artifact_id"] = "unregistered"

    result = orbit_result(con, frame)

    assert result._raw_artifact_ids == ()
    assert result.provenance.empty


def test_ambiguous_database_match_fails_closed(
    orbital_archive,
):
    con, frame = orbital_archive

    con.execute("""
        INSERT INTO orbit_elements
        SELECT *
        FROM orbit_elements
        WHERE gp_id = 101
    """)

    result = orbit_result(con, frame)

    assert result._raw_artifact_ids == ()
    assert result.provenance.empty
