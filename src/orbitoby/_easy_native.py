"""Explicit access to registered provider-native datasets."""

import re

import pandas as pd

from orbitoby._easy_result import DataResult, SourceList


def _key(value):
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _validate_options(options):
    """Prevent credential-like options entering archived request metadata."""
    forbidden = (
        "password",
        "passwd",
        "secret",
        "token",
        "apikey",
        "credential",
        "authorization",
        "cookie",
        "session",
        "privateurl",
        "headers",
        "accesskey",
    )

    for name, value in options.items():
        normalized = _key(name)

        if any(word in normalized for word in forbidden):
            raise ValueError(
                f"Do not pass credentials through {name!r}. "
                "Use the provider's secure authentication configuration."
            )

        if normalized == "archiveraw":
            raise ValueError(
                "Raw artifact archiving cannot be disabled "
                "through the beginner data API."
            )

        values = value if isinstance(value, (list, tuple)) else [value]

        for element in values:
            if isinstance(element, (dict, list, tuple, set, bytes)):
                raise TypeError(f"Nested or binary option {name!r} is not supported.")

            if isinstance(element, str) and (
                "://" in element
                or "password=" in element.casefold()
                or "token=" in element.casefold()
            ):
                raise ValueError(
                    f"Option {name!r} may contain a private URL or credential."
                )


class NativeResult(DataResult):
    """Adapter-normalized records, not an assumed canonical time series."""

    def __init__(self, frame, *, study, metadata):
        self._native_lineage_only = True
        self.dataset_name = metadata["dataset"]
        self.provider_name = metadata["source"]
        self.dataset_metadata = dict(metadata)

        super().__init__(
            frame,
            name=self.dataset_name,
            start=study.start,
            end=study.end,
            source=self.provider_name,
        )

        raw_ids = frame.attrs.get("orbitoby_raw_artifact_ids", ())
        self._raw_artifact_ids = tuple(
            value
            for value in raw_ids
            if isinstance(value, str) and value and len(value) <= 256
        )

    def info(self, topic=None):
        if topic is not None:
            return super().info(topic)

        print("Dataset:", self.dataset_name)
        print("Provider:", self.provider_name)
        print("Period requested:", self.start, "to", self.end)
        print("Records returned:", len(self.table))
        print("Representation: provider-adapter normalized records")
        print("Raw artifact: archived by Core fetch policy")

        print(
            "Data scope:",
            self.dataset_metadata.get("data_scope", "not declared"),
        )
        print(
            "Canonical metrics declared:",
            self.dataset_metadata.get("canonical_metrics", []),
        )
        print(
            "Availability:",
            self.dataset_metadata.get("availability_source", "unknown"),
        )
        print(
            "Note: returned records are not automatically "
            "converted into a scientific time series."
        )
        return self

    def sources(self):
        frame = self.table.copy()

        if frame.empty:
            frame = pd.DataFrame([{}])

        if "source" not in frame.columns:
            frame["source"] = self.provider_name

        if "dataset" not in frame.columns:
            frame["dataset"] = self.dataset_name

        if "metric" not in frame.columns:
            frame["metric"] = "not declared"

        return SourceList(frame, self.provider_name)

    def plot(self, *, kind="auto", title=None, width=900, height=360, below=None):
        required = {"timestamp", "metric", "value", "unit"}

        if not required.issubset(self.table.columns):
            missing = sorted(required - set(self.table.columns))
            raise ValueError(
                "This provider dataset is not a declared scalar "
                "time series. Missing: "
                + ", ".join(missing)
                + ". Inspect result.show() and result.info()."
            )

        if self.table.empty:
            raise ValueError("No data points are available to plot.")

        pd.to_numeric(
            self.table["value"].dropna(),
            errors="raise",
        )

        frame = self.table.copy()

        if "source" not in frame:
            frame["source"] = self.provider_name

        if "dataset" not in frame:
            frame["dataset"] = self.dataset_name

        plot_data = DataResult(
            frame,
            name=self.name,
            start=self.start,
            end=self.end,
            source=self.provider_name,
        )

        return plot_data.plot(
            kind=kind,
            title=title,
            width=width,
            height=height,
            below=below,
        )


def fetch_data(study, name, *, source=None, dataset=None, **options):
    """Resolve an explicitly registered native dataset, then fetch it."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Enter a registered dataset name.")

    _validate_options(options)

    if "start" in options or "end" in options:
        raise ValueError(
            "The study already defines start and end. "
            "Create a new study to change the period."
        )

    archive = study._core

    selected_source = None

    if source is not None:
        if not isinstance(source, str):
            raise TypeError("source must be a provider name.")

        matches = [
            item for item in archive.sources_available() if _key(item) == _key(source)
        ]

        if len(matches) != 1:
            raise ValueError(f"Unknown or ambiguous provider: {source!r}.")

        selected_source = matches[0]

    records = archive.datasets(
        source=selected_source,
        live=False,
    )

    wanted = _key(dataset or name)

    matches = [row for row in records if _key(str(row.get("dataset", ""))) == wanted]

    if not matches and dataset is None:
        matches = [
            row
            for row in records
            if any(
                _key(str(metric)) == _key(name)
                for metric in row.get("canonical_metrics", ())
            )
        ]

    if not matches:
        raise ValueError(
            f"No registered dataset matches {name!r}. "
            "Use ob.datasets().show() to inspect available names."
        )

    if len(matches) != 1:
        choices = [f"{row['source']}/{row['dataset']}" for row in matches]
        raise ValueError(
            f"Dataset {name!r} is ambiguous: {choices}. Specify source= and dataset=."
        )

    metadata = matches[0]
    provider = metadata["source"]
    product = metadata["dataset"]

    params = dict(options)

    # Apply the study's period only to temporal product scopes.
    # Static catalogues need not accept a date range.
    if metadata.get("data_scope") in {"global", "fixed_object"}:
        params["start"] = study.start
        params["end"] = study.end

    frame = archive.fetch(
        source=provider,
        dataset=product,
        archive_raw=True,
        **params,
    )

    if not isinstance(frame, pd.DataFrame):
        raise TypeError("Core fetch did not return a DataFrame.")

    return NativeResult(frame, study=study, metadata=metadata)
