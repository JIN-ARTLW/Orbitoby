"""Evidence-based, read-only lineage inspection for Easy Results."""

import pandas as pd

from orbitoby._easy_discovery import (
    CatalogList,
    _public_metadata,
    _read_archive,
)

_ARTIFACT_FIELDS = (
    "artifact_id",
    "source",
    "dataset",
    "norad_id",
    "retrieved_at",
    "sha256",
)

_RECORD_FIELDS = (
    "record_id",
    "artifact_id",
    "object_id",
    "source",
    "dataset",
    "retrieved_at",
    "row_index",
    "identity_status",
)


def verified_scientific_artifact_ids(archive, frame):
    """Attest Core canonical artifact references against persisted lineage.

    All returned rows must resolve. Otherwise no artifact is claimed
    as verified for the entire result.
    """
    required = ("artifact_id", "source", "dataset", "metric")

    if frame.empty or not set(required).issubset(frame.columns):
        return ()

    references = frame.loc[:, list(required)]

    if references.isna().any().any():
        return ()

    unique_references = references.drop_duplicates()

    sql = """
        SELECT 1
        FROM artifacts AS a
        JOIN scientific_files AS f
          ON f.artifact_id = a.artifact_id
        WHERE a.artifact_id = ?
          AND a.source = ?
          AND a.dataset = ?
          AND f.source = ?
          AND f.dataset = ?
          AND f.metric = ?
          AND f.raw_sha256 = a.sha256
        LIMIT 1
    """

    verified = set()

    for artifact_id, source, dataset, metric in unique_references.itertuples(
        index=False, name=None
    ):
        values = (artifact_id, source, dataset, metric)

        if any(not isinstance(value, str) or not value.strip() for value in values):
            return ()

        if len(artifact_id) > 256:
            return ()

        match = archive.con.execute(
            sql,
            [
                artifact_id,
                source,
                dataset,
                source,
                dataset,
                metric,
            ],
        ).fetchone()

        if match is None:
            return ()

        verified.add(artifact_id)

    return tuple(sorted(verified))


def _identifiers(result, field):
    """Return only internal archive identifiers, never provider columns."""
    if field == "artifact_id":
        values = getattr(result, "_raw_artifact_ids", ())
    elif field == "record_id":
        values = getattr(result, "_verified_record_ids", ())
    else:
        raise ValueError(f"Unsupported lineage identifier: {field}")

    return sorted(
        {
            value
            for value in values
            if isinstance(value, str) and value and len(value) <= 256
        }
    )


def _query_exact(archive, *, table, fields, filter_sql, ids):
    """Execute bounded, parameterized lookups with a safe projection."""
    batches = []

    for index in range(0, len(ids), 300):
        subset = ids[index : index + 300]
        placeholders = ", ".join("?" for _ in subset)
        projection = ", ".join(fields)

        query = (
            f"SELECT DISTINCT {projection} FROM {table} "
            f"WHERE {filter_sql.format(placeholders=placeholders)}"
        )

        batches.append(archive.con.execute(query, subset).df())

    if not batches:
        return pd.DataFrame(columns=list(fields))

    return pd.concat(batches, ignore_index=True)


def result_artifacts(result):
    """Find archived raw artifacts using proven artifact/record IDs."""
    artifact_ids = _identifiers(result, "artifact_id")
    record_ids = _identifiers(result, "record_id")

    if not artifact_ids and not record_ids:
        raise LookupError(
            "This result has no verified artifact_id or record_id. "
            "Its exact raw lineage cannot be established from "
            "provider names or study dates alone."
        )

    def read(archive):
        if artifact_ids:
            frame = _query_exact(
                archive,
                table="artifacts",
                fields=_ARTIFACT_FIELDS,
                filter_sql="artifact_id IN ({placeholders})",
                ids=artifact_ids,
            )
        else:
            # Resolve artifacts through explicitly linked source records.
            fields = tuple(f"a.{field} AS {field}" for field in _ARTIFACT_FIELDS)

            frame = _query_exact(
                archive,
                table=(
                    "artifacts a JOIN source_records r ON a.artifact_id = r.artifact_id"
                ),
                fields=fields,
                filter_sql="r.record_id IN ({placeholders})",
                ids=record_ids,
            )

        return CatalogList(
            _public_metadata(frame, _ARTIFACT_FIELDS),
            title="Raw artifacts directly linked to this result",
        )

    return _read_archive(read)


def result_records(result):
    """Inspect only source records identified by exact record IDs."""
    record_ids = _identifiers(result, "record_id")

    if not record_ids:
        raise LookupError(
            "This result does not retain exact source record_id values. "
            "Archive-wide records must not be presented as "
            "records belonging to this particular result."
        )

    def read(archive):
        frame = _query_exact(
            archive,
            table="source_records",
            fields=_RECORD_FIELDS,
            filter_sql="record_id IN ({placeholders})",
            ids=record_ids,
        )

        return CatalogList(
            _public_metadata(frame, _RECORD_FIELDS),
            title="Indexed provider records directly linked to this result",
        )

    return _read_archive(read)
