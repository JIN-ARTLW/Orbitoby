import duckdb
import pandas as pd
import pytest

from orbitoby.warehouse.scientific import ScientificStore


def connection():
    con = duckdb.connect(":memory:")

    con.execute(
        """
        CREATE TABLE artifacts (
            artifact_id VARCHAR PRIMARY KEY,
            source VARCHAR NOT NULL,
            dataset VARCHAR NOT NULL,
            norad_id INTEGER,
            requested_start DATE,
            requested_end DATE,
            retrieved_at TIMESTAMPTZ,
            sha256 VARCHAR NOT NULL,
            path VARCHAR
        )
        """
    )

    con.execute(
        """
        INSERT INTO artifacts (
            artifact_id,
            source,
            dataset,
            retrieved_at,
            sha256
        )
        VALUES (
            'artifact-1',
            'gfz',
            'kp',
            TIMESTAMPTZ '2024-01-03 00:00:00+00',
            'raw-sha-1'
        )
        """
    )

    return con


def frame():
    return pd.DataFrame(
        [
            {
                "timestamp": pd.Timestamp("2024-01-01T00:00:00Z"),
                "metric": "kp",
                "value": 3.0,
                "unit": "1",
                "source_value": 3.0,
                "is_missing": False,
                "missing_reason": None,
                "source": "gfz",
                "dataset": "kp",
                "source_field": "Kp",
                "source_version": None,
                "status": "definitive",
                "provider_status": "D",
                "quality_flag": None,
                "artifact_kind": "measurement",
                "method": None,
                "interval_start": pd.Timestamp("2024-01-01T00:00:00Z"),
                "interval_end": pd.Timestamp("2024-01-01T03:00:00Z"),
                "artifact_id": "artifact-1",
                "retrieved_at": pd.Timestamp("2024-01-03T00:00:00Z"),
                "transform": "identity",
                "transform_version": "1",
                "context": {
                    "provider": "gfz",
                },
            },
            {
                "timestamp": pd.Timestamp("2024-01-01T03:00:00Z"),
                "metric": "kp",
                "value": None,
                "unit": "1",
                "source_value": 99.9,
                "is_missing": True,
                "missing_reason": "provider_fill",
                "source": "gfz",
                "dataset": "kp",
                "source_field": "Kp",
                "source_version": None,
                "status": "definitive",
                "provider_status": "D",
                "quality_flag": None,
                "artifact_kind": "measurement",
                "method": None,
                "interval_start": pd.Timestamp("2024-01-01T03:00:00Z"),
                "interval_end": pd.Timestamp("2024-01-01T06:00:00Z"),
                "artifact_id": "artifact-1",
                "retrieved_at": pd.Timestamp("2024-01-03T00:00:00Z"),
                "transform": "identity",
                "transform_version": "1",
                "context": {
                    "provider": "gfz",
                    "flag": None,
                },
            },
        ]
    )


def test_write_read_round_trip(tmp_path):
    con = connection()

    store = ScientificStore(
        con,
        root=tmp_path,
    )

    saved = store.write(
        frame(),
        requested_start="2024-01-01T00:00:00Z",
        requested_end="2024-01-02T00:00:00Z",
    )

    assert saved.path.is_file()
    assert saved.row_count == 2

    result = store.read_store(saved.store_id)

    assert len(result) == 2
    assert result["timestamp"].dt.tz is not None
    assert result.loc[0, "value"] == 3.0
    assert pd.isna(result.loc[1, "value"])
    assert result.loc[1, "is_missing"]
    assert result.loc[1, "missing_reason"] == "provider_fill"
    assert result.loc[1, "source_value"] == 99.9
    assert result.loc[0, "provider_status"] == "D"
    assert result.loc[0, "context"] == {"provider": "gfz"}


def test_write_is_idempotent(tmp_path):
    con = connection()
    store = ScientificStore(con, root=tmp_path)

    first = store.write(
        frame(),
        requested_start="2024-01-01",
        requested_end="2024-01-02",
    )

    second = store.write(
        frame(),
        requested_start="2024-01-01",
        requested_end="2024-01-02",
    )

    assert first.store_id == second.store_id
    assert first.path == second.path

    count = con.execute(
        """
        SELECT COUNT(*)
        FROM scientific_files
        """
    ).fetchone()[0]

    assert count == 1


def test_rejects_missing_artifact_id(tmp_path):
    con = connection()
    store = ScientificStore(con, root=tmp_path)

    data = frame()
    data["artifact_id"] = None

    with pytest.raises(
        ValueError,
        match="artifact_id",
    ):
        store.write(
            data,
            requested_start="2024-01-01",
            requested_end="2024-01-02",
        )


def test_rejects_unregistered_artifact(tmp_path):
    con = connection()
    store = ScientificStore(con, root=tmp_path)

    data = frame()
    data["artifact_id"] = "unknown"

    with pytest.raises(
        ValueError,
        match="unregistered",
    ):
        store.write(
            data,
            requested_start="2024-01-01",
            requested_end="2024-01-02",
        )


def test_rejects_row_outside_half_open_window(
    tmp_path,
):
    con = connection()
    store = ScientificStore(con, root=tmp_path)

    data = frame()

    data.loc[
        1,
        "timestamp",
    ] = pd.Timestamp("2024-01-02T00:00:00Z")

    with pytest.raises(
        ValueError,
        match=r"\[start, end\)",
    ):
        store.write(
            data,
            requested_start="2024-01-01",
            requested_end="2024-01-02",
        )


def test_transform_version_changes_identity(
    tmp_path,
):
    con = connection()
    store = ScientificStore(con, root=tmp_path)

    first = store.write(
        frame(),
        requested_start="2024-01-01",
        requested_end="2024-01-02",
    )

    data = frame()
    data["transform_version"] = "2"

    second = store.write(
        data,
        requested_start="2024-01-01",
        requested_end="2024-01-02",
    )

    assert first.store_id != second.store_id


def test_corruption_is_detected(tmp_path):
    con = connection()
    store = ScientificStore(con, root=tmp_path)

    saved = store.write(
        frame(),
        requested_start="2024-01-01",
        requested_end="2024-01-02",
    )

    with saved.path.open("ab") as handle:
        handle.write(b"corruption")

    with pytest.raises(
        RuntimeError,
        match="checksum",
    ):
        store.read_store(saved.store_id)


def test_failed_write_leaves_no_registered_file(
    tmp_path,
    monkeypatch,
):
    con = connection()
    store = ScientificStore(con, root=tmp_path)

    def fail_write(*args, **kwargs):
        raise RuntimeError("simulated write failure")

    monkeypatch.setattr(
        store,
        "_write_parquet",
        fail_write,
    )

    with pytest.raises(
        RuntimeError,
        match="simulated",
    ):
        store.write(
            frame(),
            requested_start="2024-01-01",
            requested_end="2024-01-02",
        )

    count = con.execute(
        """
        SELECT COUNT(*)
        FROM scientific_files
        """
    ).fetchone()[0]

    assert count == 0
    assert list(tmp_path.rglob("*.parquet")) == []


def test_query_does_not_silently_deduplicate(
    tmp_path,
):
    con = connection()
    store = ScientificStore(con, root=tmp_path)

    store.write(
        frame(),
        requested_start="2024-01-01",
        requested_end="2024-01-02",
    )

    data = frame()
    data["transform_version"] = "2"

    store.write(
        data,
        requested_start="2024-01-01",
        requested_end="2024-01-02",
    )

    result = store.query(
        metric="kp",
        source="gfz",
        dataset="kp",
        start="2024-01-01",
        end="2024-01-02",
    )

    assert len(result) == 4


def test_missing_ranges_are_half_open(
    tmp_path,
):
    con = connection()
    store = ScientificStore(
        con,
        root=tmp_path,
    )

    first_data = frame().iloc[[0]].copy()

    first = store.write(
        first_data,
        requested_start="2024-01-01T00:00:00Z",
        requested_end="2024-01-01T02:00:00Z",
    )

    store.record_coverage(
        metric="kp",
        source="gfz",
        dataset="kp",
        artifact_id="artifact-1",
        transform="identity",
        transform_version="1",
        requested_start="2024-01-01T00:00:00Z",
        requested_end="2024-01-01T02:00:00Z",
        row_count=1,
        store_id=first.store_id,
    )

    second_data = frame().iloc[[0]].copy()
    second_data["timestamp"] = pd.Timestamp("2024-01-01T03:00:00Z")

    second = store.write(
        second_data,
        requested_start="2024-01-01T03:00:00Z",
        requested_end="2024-01-01T04:00:00Z",
    )

    store.record_coverage(
        metric="kp",
        source="gfz",
        dataset="kp",
        artifact_id="artifact-1",
        transform="identity",
        transform_version="1",
        requested_start="2024-01-01T03:00:00Z",
        requested_end="2024-01-01T04:00:00Z",
        row_count=1,
        store_id=second.store_id,
    )

    result = store.missing_ranges(
        metric="kp",
        source="gfz",
        dataset="kp",
        transform="identity",
        transform_version="1",
        start="2024-01-01T00:00:00Z",
        end="2024-01-01T05:00:00Z",
    )

    assert result == [
        (
            pd.Timestamp("2024-01-01T02:00:00Z"),
            pd.Timestamp("2024-01-01T03:00:00Z"),
        ),
        (
            pd.Timestamp("2024-01-01T04:00:00Z"),
            pd.Timestamp("2024-01-01T05:00:00Z"),
        ),
    ]


def test_parquet_read_ignores_hive_partition_columns(
    tmp_path,
):
    con = connection()
    store = ScientificStore(
        con,
        root=tmp_path,
    )

    saved = store.write(
        frame(),
        requested_start="2024-01-01",
        requested_end="2024-01-02",
    )

    disk = store._read_parquet_disk(saved.path)

    assert tuple(disk.columns) == (
        "timestamp",
        "metric",
        "value",
        "unit",
        "source_value_json",
        "is_missing",
        "missing_reason",
        "source",
        "dataset",
        "source_field",
        "source_version",
        "status",
        "provider_status_json",
        "quality_flag_json",
        "artifact_kind",
        "method",
        "interval_start",
        "interval_end",
        "artifact_id",
        "retrieved_at",
        "transform",
        "transform_version",
        "context_json",
    )

    assert "year" not in disk.columns


def test_nullable_string_does_not_stringify_nan():
    disk = ScientificStore._disk_frame(frame())

    missing_reason = disk.loc[
        0,
        "missing_reason",
    ]

    assert pd.isna(missing_reason)
    assert not isinstance(
        missing_reason,
        str,
    )


def test_logical_hash_is_timezone_invariant():
    disk = ScientificStore._disk_frame(frame())

    shifted = disk.copy()

    for column in (
        "timestamp",
        "interval_start",
        "interval_end",
        "retrieved_at",
    ):
        shifted[column] = shifted[column].dt.tz_convert("Asia/Seoul")

    assert ScientificStore._logical_sha256(disk) == ScientificStore._logical_sha256(
        shifted
    )


def test_scientific_store_connection_is_utc(
    tmp_path,
):
    con = connection()

    ScientificStore(
        con,
        root=tmp_path,
    )

    timezone = con.execute(
        """
        SELECT current_setting('TimeZone')
        """
    ).fetchone()[0]

    assert timezone == "UTC"


def test_zero_row_success_is_real_coverage(
    tmp_path,
):
    con = connection()

    store = ScientificStore(
        con,
        root=tmp_path,
    )

    store.record_coverage(
        metric="kp",
        source="gfz",
        dataset="kp",
        artifact_id="artifact-1",
        transform="identity",
        transform_version="1",
        requested_start="2024-01-01T00:00:00Z",
        requested_end="2024-01-02T00:00:00Z",
        row_count=0,
        store_id=None,
    )

    assert (
        store.missing_ranges(
            metric="kp",
            source="gfz",
            dataset="kp",
            transform="identity",
            transform_version="1",
            start="2024-01-01T00:00:00Z",
            end="2024-01-02T00:00:00Z",
        )
        == []
    )

    count = con.execute(
        """
        SELECT COUNT(*)
        FROM scientific_files
        """
    ).fetchone()[0]

    assert count == 0


def test_coverage_is_transform_version_scoped(
    tmp_path,
):
    con = connection()

    store = ScientificStore(
        con,
        root=tmp_path,
    )

    store.record_coverage(
        metric="kp",
        source="gfz",
        dataset="kp",
        artifact_id="artifact-1",
        transform="identity",
        transform_version="1",
        requested_start="2024-01-01T00:00:00Z",
        requested_end="2024-01-02T00:00:00Z",
        row_count=0,
        store_id=None,
    )

    result = store.missing_ranges(
        metric="kp",
        source="gfz",
        dataset="kp",
        transform="identity",
        transform_version="2",
        start="2024-01-01T00:00:00Z",
        end="2024-01-02T00:00:00Z",
    )

    assert result == [
        (
            pd.Timestamp("2024-01-01T00:00:00Z"),
            pd.Timestamp("2024-01-02T00:00:00Z"),
        )
    ]


def test_db_registration_failure_removes_replaced_parquet(
    tmp_path,
):
    con = connection()
    store = ScientificStore(
        con,
        root=tmp_path,
    )

    class FailingConnection:
        def __init__(
            self,
            wrapped,
        ):
            self.wrapped = wrapped

        def execute(
            self,
            sql,
            parameters=None,
        ):
            if "INSERT INTO scientific_files" in str(sql):
                raise RuntimeError("simulated DB registration failure")

            if parameters is None:
                return self.wrapped.execute(sql)

            return self.wrapped.execute(
                sql,
                parameters,
            )

        def executemany(
            self,
            sql,
            parameters,
        ):
            return self.wrapped.executemany(
                sql,
                parameters,
            )

    store.con = FailingConnection(con)

    with pytest.raises(
        RuntimeError,
        match="simulated DB registration failure",
    ):
        store.write(
            frame(),
            requested_start="2024-01-01",
            requested_end="2024-01-02",
        )

    count = con.execute(
        """
        SELECT COUNT(*)
        FROM scientific_files
        """
    ).fetchone()[0]

    assert count == 0

    assert list(tmp_path.rglob("*.parquet")) == []

    assert list(tmp_path.rglob("*.tmp")) == []
