import json
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from orbitoby.archive.raw import RawArtifact
from orbitoby.warehouse.identity import (
    SCHEMA,
    IdentityStore,
)


def artifact():
    return RawArtifact(
        artifact_id="artifact-test",
        source="gcat",
        dataset="satcat",
        norad_id=None,
        requested_start=None,
        requested_end=None,
        retrieved_at=datetime.now(UTC),
        sha256="0" * 64,
        path=Path("/tmp/fake.tsv"),
    )


def connection():
    con = duckdb.connect(":memory:")
    con.execute(SCHEMA)
    return con


def test_native_fields_are_preserved_without_eav_explosion():
    con = connection()

    rows = [
        {
            "JCAT": "S00001",
            "Satcat": "25544",
            "Piece": "1998-067A",
            "Name": "ISS",
            "Mass": "420000",
            "State": "US",
            "Status": "O",
            "Extra1": "a",
            "Extra2": "b",
            "Extra3": "c",
        }
    ]

    IdentityStore(con).ingest(
        rows,
        artifact(),
    )

    source_row = con.execute(
        """
        SELECT data
        FROM source_records
        """
    ).fetchone()

    data = json.loads(source_row[0])

    assert data["Extra1"] == "a"
    assert data["Extra3"] == "c"

    property_count = con.execute(
        """
        SELECT count(*)
        FROM object_properties
        """
    ).fetchone()[0]

    assert property_count <= 4


def test_identity_uses_explicit_identifiers_not_names():
    con = connection()

    rows = [
        {
            "JCAT": "S00001",
            "Satcat": "25544",
            "Piece": "1998-067A",
            "Name": "Same Name",
        },
        {
            "JCAT": "S00002",
            "Satcat": "20580",
            "Piece": "1990-037B",
            "Name": "Same Name",
        },
    ]

    IdentityStore(con).ingest(
        rows,
        artifact(),
    )

    count = con.execute(
        """
        SELECT count(*)
        FROM objects
        """
    ).fetchone()[0]

    assert count == 2


def test_batch_ingest_is_atomic():
    con = connection()
    store = IdentityStore(con)

    good = [
        {
            "JCAT": "S00001",
            "Satcat": "25544",
            "Piece": "1998-067A",
            "Name": "ISS",
        }
    ]

    bad = [
        {
            "JCAT": "S00002",
            "Satcat": "20580",
            "Piece": "1990-037B",
            "Name": "HST",
            "bad": float("nan"),
        }
    ]

    try:
        store.ingest_batches(
            [good, bad],
            artifact(),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected serialization failure")

    assert con.execute("SELECT count(*) FROM source_records").fetchone()[0] == 0


def test_batch_commit_is_resumable():
    con = connection()
    store = IdentityStore(con)

    first = [
        {
            "JCAT": "S00001",
            "Satcat": "25544",
            "Piece": "1998-067A",
            "Name": "ISS",
        }
    ]

    broken = [
        {
            "JCAT": "S00002",
            "Satcat": "20580",
            "Piece": "1990-037B",
            "Name": "HST",
            "bad": float("nan"),
        }
    ]

    try:
        store.ingest_batches(
            [first, broken],
            artifact(),
            commit_each_batch=True,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected serialization failure")

    # The completed first batch survives.
    assert con.execute("SELECT count(*) FROM source_records").fetchone()[0] == 1

    # Retrying the completed batch is idempotent.
    count = store.ingest_batches(
        [first],
        artifact(),
        commit_each_batch=True,
    )

    assert count == 1

    assert con.execute("SELECT count(*) FROM source_records").fetchone()[0] == 1
