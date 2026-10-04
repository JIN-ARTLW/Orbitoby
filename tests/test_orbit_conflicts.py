from types import SimpleNamespace

import pytest

from orbitoby import Archive
from orbitoby.sources.spacetrack import SpaceTrackSource
from orbitoby.warehouse import db


@pytest.fixture
def archive(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "archive.duckdb")
    monkeypatch.setattr(db, "ensure_data_dirs", lambda: None)
    result = Archive.__new__(Archive)
    result.con = db.connect_db()
    yield result
    result.close()


def record(periapsis):
    return SpaceTrackSource()._normalize_gp(
        {
            "GP_ID": "1",
            "NORAD_CAT_ID": "39452",
            "EPOCH": "2024-05-10T00:00:00Z",
            "PERIAPSIS": str(periapsis),
        }
    )


def insert(archive, records, artifact_id="a"):
    archive._insert_orbit_records(
        records=records,
        artifact=SimpleNamespace(artifact_id=artifact_id),
        source_name="spacetrack",
    )


def test_identical_gp_record_is_idempotent(archive):
    insert(archive, [record(400)])
    insert(archive, [record(400)], "b")
    assert archive.con.execute(
        "SELECT count(*), min(artifact_id) FROM orbit_elements"
    ).fetchone() == (1, "a")


def test_conflicting_stored_gp_is_rejected(archive):
    insert(archive, [record(400)])
    with pytest.raises(ValueError, match="Conflicting orbital claims"):
        insert(archive, [record(500)], "b")
    assert archive.con.execute(
        "SELECT periapsis_km FROM orbit_elements"
    ).fetchone() == (400.0,)


def test_conflicting_gp_within_batch_is_rejected(archive):
    with pytest.raises(ValueError, match="Conflicting orbital claims"):
        insert(archive, [record(400), record(500)])
    assert archive.con.execute("SELECT count(*) FROM orbit_elements").fetchone() == (0,)
