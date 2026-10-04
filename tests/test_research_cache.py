from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pandas as pd

from orbitoby.archive.raw import RawArtifact
from orbitoby.research import ResearchAPI
from orbitoby.warehouse.scientific import (
    ScientificStore,
)


class CachedArchive(ResearchAPI):
    def __init__(
        self,
        tmp_path: Path,
        *,
        empty: bool = False,
    ):
        self.con = duckdb.connect(":memory:")

        self.con.execute("SET TimeZone = 'UTC'")

        self.con.execute(
            """
            CREATE TABLE artifacts (
                artifact_id VARCHAR PRIMARY KEY,
                source VARCHAR NOT NULL,
                dataset VARCHAR NOT NULL,
                norad_id INTEGER,
                requested_start DATE,
                requested_end DATE,
                retrieved_at TIMESTAMPTZ NOT NULL,
                sha256 VARCHAR NOT NULL,
                path VARCHAR NOT NULL
            )
            """
        )

        self.scientific_store = ScientificStore(
            self.con,
            root=tmp_path / "canonical",
        )

        self.tmp_path = tmp_path
        self.calls = []
        self.empty = empty

    def _fetch_records(
        self,
        *,
        source,
        dataset,
        archive_raw=True,
        **params,
    ):
        self.calls.append(
            {
                "source": source,
                "dataset": dataset,
                **params,
            }
        )

        start = pd.Timestamp(
            params.get(
                "start",
                "2024-01-01T00:00:00Z",
            )
        )

        end = pd.Timestamp(
            params.get(
                "end",
                "2024-01-02T00:00:00Z",
            )
        )

        if start.tzinfo is None:
            start = start.tz_localize("UTC")
        else:
            start = start.tz_convert("UTC")

        if end.tzinfo is None:
            end = end.tz_localize("UTC")
        else:
            end = end.tz_convert("UTC")

        artifact = None

        if archive_raw:
            number = len(self.calls)

            artifact_id = f"artifact-{number}"

            path = self.tmp_path / f"{artifact_id}.json"

            path.write_bytes(b"{}")

            retrieved_at = datetime.now(UTC)

            artifact = RawArtifact(
                artifact_id=artifact_id,
                source=source,
                dataset=dataset,
                norad_id=None,
                requested_start=(start.date()),
                requested_end=(end.date()),
                retrieved_at=retrieved_at,
                sha256=f"sha-{number}",
                path=path,
            )

            self.con.execute(
                """
                INSERT INTO artifacts (
                    artifact_id,
                    source,
                    dataset,
                    norad_id,
                    requested_start,
                    requested_end,
                    retrieved_at,
                    sha256,
                    path
                )
                VALUES (
                    ?, ?, ?, NULL,
                    ?, ?, ?, ?, ?
                )
                """,
                [
                    artifact_id,
                    source,
                    dataset,
                    start.date(),
                    end.date(),
                    retrieved_at,
                    f"sha-{number}",
                    str(path),
                ],
            )

        if self.empty:
            return [], artifact

        records = []

        timestamp = start

        while timestamp < end:
            records.append(
                {
                    "datetime": (
                        timestamp.isoformat().replace(
                            "+00:00",
                            "Z",
                        )
                    ),
                    "Kp": 3.0,
                    "status": "def",
                }
            )

            timestamp += pd.Timedelta(hours=3)

        return records, artifact


def test_second_query_uses_local_cache(
    tmp_path,
):
    archive = CachedArchive(tmp_path)

    first = archive.timeseries(
        "kp",
        source="gfz",
        dataset="kp",
        start="2024-01-01T00:00:00Z",
        end="2024-01-01T06:00:00Z",
    )

    assert len(archive.calls) == 1
    assert len(first) == 2

    second = archive.timeseries(
        "kp",
        source="gfz",
        dataset="kp",
        start="2024-01-01T00:00:00Z",
        end="2024-01-01T06:00:00Z",
    )

    assert len(archive.calls) == 1
    assert len(second) == 2

    assert first["timestamp"].tolist() == second["timestamp"].tolist()

    assert first["value"].tolist() == second["value"].tolist()


def test_extension_fetches_only_missing_range(
    tmp_path,
):
    archive = CachedArchive(tmp_path)

    archive.timeseries(
        "kp",
        source="gfz",
        dataset="kp",
        start="2024-01-01T00:00:00Z",
        end="2024-01-01T06:00:00Z",
    )

    archive.timeseries(
        "kp",
        source="gfz",
        dataset="kp",
        start="2024-01-01T00:00:00Z",
        end="2024-01-01T09:00:00Z",
    )

    assert len(archive.calls) == 2

    second = archive.calls[1]

    assert pd.Timestamp(second["start"]) == pd.Timestamp("2024-01-01T06:00:00Z")

    assert pd.Timestamp(second["end"]) == pd.Timestamp("2024-01-01T09:00:00Z")


def test_zero_row_success_is_cached(
    tmp_path,
):
    archive = CachedArchive(
        tmp_path,
        empty=True,
    )

    first = archive.timeseries(
        "kp",
        source="gfz",
        dataset="kp",
        start="2024-01-01T00:00:00Z",
        end="2024-01-02T00:00:00Z",
    )

    assert first.empty
    assert len(archive.calls) == 1

    second = archive.timeseries(
        "kp",
        source="gfz",
        dataset="kp",
        start="2024-01-01T00:00:00Z",
        end="2024-01-02T00:00:00Z",
    )

    assert second.empty
    assert len(archive.calls) == 1


def test_archive_raw_false_bypasses_cache(
    tmp_path,
):
    archive = CachedArchive(tmp_path)

    archive.timeseries(
        "kp",
        source="gfz",
        dataset="kp",
        start="2024-01-01T00:00:00Z",
        end="2024-01-01T06:00:00Z",
        archive_raw=False,
    )

    archive.timeseries(
        "kp",
        source="gfz",
        dataset="kp",
        start="2024-01-01T00:00:00Z",
        end="2024-01-01T06:00:00Z",
        archive_raw=False,
    )

    assert len(archive.calls) == 2

    count = archive.con.execute(
        """
        SELECT COUNT(*)
        FROM scientific_coverage
        """
    ).fetchone()[0]

    assert count == 0
