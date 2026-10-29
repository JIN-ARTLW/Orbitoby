"""Beginner discovery backed by the existing Archive registry."""

import importlib
import re
from types import ModuleType

import pandas as pd


def _normalized(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Enter a non-empty name.")
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _read_archive(callback):
    from orbitoby.service import Archive

    archive = Archive()
    try:
        return callback(archive)
    finally:
        archive.close()


def _source_name(archive, name):
    wanted = _normalized(name)
    matches = [
        candidate
        for candidate in archive.sources_available()
        if _normalized(candidate) == wanted
    ]

    if len(matches) == 1:
        return matches[0]

    if not matches:
        available = ", ".join(archive.sources_available())
        raise ValueError(f"Unknown source {name!r}. Available: {available}")

    raise ValueError(f"Ambiguous source name: {name!r}")


class CatalogList:
    """A browsable, detached snapshot of registered metadata."""

    def __init__(self, records, *, title):
        self._records = [dict(record) for record in records]
        self.title = title

    @property
    def table(self):
        return pd.DataFrame(self._records)

    def __len__(self):
        return len(self._records)

    def show(self, rows=20):
        if not isinstance(rows, int) or rows < 1:
            raise ValueError("rows must be a positive integer.")

        table = self.table

        print(f"{self.title}: {len(table)} registered entries")

        if table.empty:
            print("No matching registered entries.")
            return self

        preview = table.head(rows)

        try:
            from IPython.display import display
        except ImportError:
            print(preview.to_string(index=False))
        else:
            display(preview)

        if len(table) > rows:
            print(
                f"Showing {rows} of {len(table)}. "
                "Use .show(rows=...) or .table for more."
            )

        return self


class CatalogItem:
    """Information about one registered provider or dataset."""

    def __init__(self, record, *, kind):
        self._record = dict(record)
        self.kind = kind

    @property
    def table(self):
        return pd.DataFrame([self._record])

    def info(self):
        print(f"Registered {self.kind} information")

        for key, value in self._record.items():
            print(f"{key}: {value}")

        print(
            "\nRegistered metadata does not guarantee "
            "live availability or successful retrieval."
        )
        return self


def sources():
    """List registered providers without contacting their endpoints."""
    return _read_archive(
        lambda archive: CatalogList(
            archive.source_info(),
            title="Orbitoby sources",
        )
    )


def source(name):
    """Inspect one registered source."""

    def read(archive):
        chosen = _source_name(archive, name)
        return CatalogItem(
            archive.source_info(chosen),
            kind="source",
        )

    return _read_archive(read)


def datasets(
    query=None,
    *,
    source=None,
    metric=None,
    category=None,
    live=False,
):
    """Search actual curated datasets, offline by default."""
    if query is not None and (not isinstance(query, str) or not query.strip()):
        raise ValueError("query must be a non-empty search string.")

    if not isinstance(live, bool):
        raise TypeError("live must be True or False.")

    if live and not any((source, metric, category)):
        raise ValueError(
            "live=True may contact many providers. "
            "Specify source=, metric= or category= first."
        )

    def read(archive):
        chosen = _source_name(archive, source) if source is not None else None

        records = archive.datasets(
            source=chosen,
            metric=metric,
            category=category,
            live=live,
        )

        if query is not None:
            search = query.strip().casefold()

            records = [
                record
                for record in records
                if search
                in " ".join(str(value) for value in record.values()).casefold()
            ]

        return CatalogList(
            records,
            title="Orbitoby datasets",
        )

    return _read_archive(read)


def _dataset_id(record):
    for key in (
        "dataset",
        "dataset_id",
        "id",
        "name",
    ):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value

    return None


def dataset(name, source=None, *, live=False):
    """Inspect one dataset, rejecting ambiguous source selection."""
    wanted = _normalized(name)

    def read(archive):
        chosen = _source_name(archive, source) if source is not None else None

        records = archive.datasets(
            source=chosen,
            live=live,
        )

        exact = [
            record
            for record in records
            if _dataset_id(record) is not None
            and _normalized(_dataset_id(record)) == wanted
        ]

        # A canonical metric may identify a different native
        # dataset name. Accept it only if unambiguous.
        if not exact:
            exact = [
                record
                for record in records
                if any(
                    _normalized(str(metric)) == wanted
                    for metric in record.get("canonical_metrics", ())
                )
            ]

        if not exact:
            raise ValueError(
                f'Dataset {name!r} is not registered. Try ob.datasets("...").show().'
            )

        if len(exact) != 1:
            candidates = [
                (
                    record.get("source"),
                    _dataset_id(record),
                )
                for record in exact
            ]
            raise ValueError(
                f"Dataset {name!r} is ambiguous: {candidates}. "
                "Specify source= and the exact native dataset."
            )

        record = exact[0]
        actual_source = record["source"]
        actual_dataset = _dataset_id(record)

        if actual_dataset is None:
            raise ValueError("Registered dataset metadata lacks an identifier.")

        return CatalogItem(
            archive.dataset_info(
                actual_source,
                actual_dataset,
                live=live,
            ),
            kind="dataset",
        )

    return _read_archive(read)


class _CallableSourcesPackage(ModuleType):
    """Preserve orbitoby.sources as a Python package and callable API."""

    def __call__(self):
        return sources()


def install_sources_entrypoint():
    package = importlib.import_module("orbitoby.sources")

    if not isinstance(package, _CallableSourcesPackage):
        package.__class__ = _CallableSourcesPackage


def credits():
    """Show credited registered providers from the existing Core."""
    return _read_archive(
        lambda archive: CatalogList(
            archive.credits(),
            title="Orbitoby provider credits",
        )
    )


def licenses():
    """Show registered provider policies without inferring permissions."""
    return _read_archive(
        lambda archive: CatalogList(
            archive.licenses(),
            title="Orbitoby provider licenses and policies",
        )
    )


# Only explicitly reviewed public-facing fields are exposed.
# Raw artifact paths, request parameters, and private metadata
# remain accessible through the existing Core for advanced use.
_ARTIFACT_PUBLIC_FIELDS = (
    "artifact_id",
    "id",
    "source",
    "dataset",
    "norad_id",
    "retrieved_at",
    "start",
    "end",
    "sha256",
    "size_bytes",
    "extension",
)

_PLUGIN_PUBLIC_FIELDS = (
    "name",
    "distribution",
    "version",
    "entry_point",
    "module",
    "status",
    "trusted",
)

_SENSITIVE_TEXT = re.compile(
    r"https?://|"
    r"bearer\s+\S+|"
    r"(?:password|passwd|secret|token|api[_-]?key|"
    r"cookie|authorization|session)\s*[:=]",
    re.IGNORECASE,
)


def _public_metadata(records, allowed_fields):
    """Project registered metadata onto explicitly safe display fields."""
    if isinstance(records, pd.DataFrame):
        rows = records.to_dict("records")
    else:
        rows = [dict(record) for record in records]

    output = []

    for record in rows:
        public = {}

        for field in allowed_fields:
            if field not in record:
                continue

            value = record[field]

            if isinstance(value, str):
                public[field] = "[REDACTED]" if _SENSITIVE_TEXT.search(value) else value
            elif isinstance(value, (dict, list, tuple, set, bytes)):
                public[field] = "[not shown]"
            elif (
                isinstance(
                    value,
                    (int, float, bool, pd.Timestamp),
                )
                or value is None
            ):
                public[field] = value
            else:
                public[field] = "[not shown]"

        output.append(public)

    return output


def artifacts(*, source=None, dataset=None, norad_id=None):
    """List stored raw artifacts without exposing private local paths."""
    if norad_id is not None and (
        isinstance(norad_id, bool) or not isinstance(norad_id, int) or norad_id <= 0
    ):
        raise ValueError("norad_id must be a positive integer.")

    for field_name, value in (
        ("source", source),
        ("dataset", dataset),
    ):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"{field_name} must be a non-empty string.")

    def read(archive):
        original = archive.artifacts(
            source=source,
            dataset=dataset,
            norad_id=norad_id,
        )

        return CatalogList(
            _public_metadata(
                original,
                _ARTIFACT_PUBLIC_FIELDS,
            ),
            title="Orbitoby locally archived raw artifacts",
        )

    return _read_archive(read)


def plugins():
    """List plugin candidates; discovery is not proof of trust."""

    def read(archive):
        candidates = _public_metadata(
            archive.plugin_candidates(),
            _PLUGIN_PUBLIC_FIELDS,
        )

        for candidate in candidates:
            candidate["meaning"] = "discovered candidate; inspect trust before use"

        return CatalogList(
            candidates,
            title="Orbitoby discovered plugin candidates",
        )

    return _read_archive(read)
