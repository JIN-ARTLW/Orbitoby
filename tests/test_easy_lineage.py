import duckdb
import pandas as pd
import pytest

from orbitoby._easy_result import DataResult


class FakeArchive:
    def __init__(self):
        self.con = duckdb.connect(":memory:")

        self.con.execute("""
            CREATE TABLE artifacts (
                artifact_id VARCHAR,
                source VARCHAR,
                dataset VARCHAR,
                norad_id BIGINT,
                retrieved_at VARCHAR,
                sha256 VARCHAR,
                path VARCHAR,
                metadata VARCHAR
            )
        """)

        self.con.execute("""
            CREATE TABLE source_records (
                record_id VARCHAR,
                artifact_id VARCHAR,
                object_id VARCHAR,
                source VARCHAR,
                dataset VARCHAR,
                retrieved_at VARCHAR,
                row_index INTEGER,
                identity_status VARCHAR,
                data VARCHAR
            )
        """)

        for suffix in ("1", "2"):
            self.con.execute(
                """
                INSERT INTO artifacts VALUES (
                    ?, 'spacetrack', 'gp_history',
                    39452, '2024-05-10', 'checksum',
                    '/private/file', 'PRIVATE_PASSWORD'
                )
                """,
                [f"a-{suffix}"],
            )

            self.con.execute(
                """
                INSERT INTO source_records VALUES (
                    ?, ?, 'object-1', 'spacetrack',
                    'gp_history', '2024-05-10',
                    0, 'resolved', 'PRIVATE_PASSWORD'
                )
                """,
                [f"r-{suffix}", f"a-{suffix}"],
            )

    def close(self):
        self.con.close()


@pytest.fixture
def archive(monkeypatch):
    from orbitoby import service

    # Each lookup gets its own Archive and database connection.
    # The production helper closes that connection after use.
    monkeypatch.setattr(service, "Archive", FakeArchive)

    return FakeArchive


def make_result(**columns):
    return DataResult(
        pd.DataFrame(columns),
        name="historical orbit",
        start="2024-05-10",
        end="2024-05-20",
        source="spacetrack",
    )


def test_artifacts_use_only_exact_identifiers(archive):
    result = make_result(
        artifact_id=["a-1"],
        value=[1],
    )

    result._raw_artifact_ids = ("a-1",)
    table = result.artifacts().table

    assert table["artifact_id"].tolist() == ["a-1"]
    assert "path" not in table
    assert "metadata" not in table


def test_records_use_only_exact_record_ids(archive):
    result = make_result(
        record_id=["r-2"],
        value=[2],
    )

    result._verified_record_ids = ("r-2",)
    table = result.records().table

    assert table["record_id"].tolist() == ["r-2"]
    assert "data" not in table


def test_artifacts_can_follow_exact_record_id(archive):
    result = make_result(
        record_id=["r-1"],
        value=[1],
    )

    result._verified_record_ids = ("r-1",)
    table = result.artifacts().table

    assert table["artifact_id"].tolist() == ["a-1"]


def test_missing_lineage_is_not_invented(archive):
    result = make_result(
        source=["spacetrack"],
        norad_id=[39452],
        value=[1],
    )

    with pytest.raises(LookupError, match="no verified"):
        result.artifacts()

    with pytest.raises(LookupError, match="exact source record_id"):
        result.records()


def test_private_content_is_not_exported_to_result(capsys, archive):
    result = make_result(
        artifact_id=["a-1"],
        record_id=["r-1"],
    )

    result._raw_artifact_ids = ("a-1",)
    result._verified_record_ids = ("r-1",)
    result.artifacts().show()
    result.records().show()

    text = capsys.readouterr().out

    assert "PRIVATE_PASSWORD" not in text
    assert "/private/file" not in text
    assert "a-2" not in text
    assert "r-2" not in text
