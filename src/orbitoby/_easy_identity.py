"""Locally indexed object identity and search results."""

from copy import deepcopy

import pandas as pd

from orbitoby._easy_result import DataResult, SourceList

_IDENTITY_FIELDS = (
    "object_id",
    "norad_id",
    "cospar_id",
    "name",
    "object_type",
    "identity_status",
    "launch_date",
    "decay_date",
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


class ObjectResult(DataResult):
    """One indexed object's identity, including original Core details."""

    def __init__(self, original):
        from orbitoby._easy_discovery import _public_metadata

        if not isinstance(original, dict):
            raise TypeError("Core object() must return a dictionary.")

        # Preserve complete Core output for deliberate advanced inspection.
        self._original = deepcopy(original)

        summary = _public_metadata(
            [original],
            _IDENTITY_FIELDS,
        )

        super().__init__(
            pd.DataFrame(summary),
            name="Locally indexed object identity",
            start=None,
            end=None,
            source="local-archive-index",
        )
        self._archive_scope = True

    @property
    def details(self):
        """Full original Core output; may contain provider-native data."""
        return deepcopy(self._original)

    def info(self, topic=None):
        if topic not in (None, "identity", "records", "scope"):
            raise ValueError(
                "Choose info(), info('identity'), info('records') or info('scope')."
            )

        print("Object identity from the local archive")
        print("Scope: all locally indexed records, not study-period filtered")
        print(
            "Provider source records:",
            len(self._original.get("source_records", [])),
        )
        print(
            "Recorded properties:",
            len(self._original.get("properties", [])),
        )
        print(
            "Recorded identifiers:",
            len(self._original.get("identifiers", [])),
        )
        return self

    def records(self):
        from orbitoby._easy_discovery import (
            CatalogList,
            _public_metadata,
        )

        records = self._original.get("source_records", [])

        return CatalogList(
            _public_metadata(records, _RECORD_FIELDS),
            title="Indexed provider records for this object",
        )

    def sources(self):
        records = self._original.get("source_records", [])
        frame = pd.DataFrame(records)

        if "source" not in frame:
            frame["source"] = pd.Series(dtype="str")
        if "dataset" not in frame:
            frame["dataset"] = pd.Series(dtype="str")
        if "metric" not in frame:
            frame["metric"] = "not declared"

        return SourceList(frame, "local-archive-index")


class SearchResult(DataResult):
    """Unmodified locally indexed object-search rows."""

    def __init__(self, frame):
        super().__init__(
            frame,
            name="Locally indexed object search",
            start=None,
            end=None,
            source="local-archive-index",
        )
        self._archive_scope = True

    def info(self, topic=None):
        if topic not in (None, "scope"):
            raise ValueError("Use info() or info('scope').")

        print("Search: locally indexed space objects")
        print("Matching objects:", len(self.table))
        print("Scope: all locally indexed records")
        print("Study dates do not filter this local index search.")
        print("For a historical population, use study.satellites().")
        return self
