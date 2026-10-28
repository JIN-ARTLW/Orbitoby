"""Human-friendly results without changing scientific values."""

from pathlib import Path

import pandas as pd


class SourceList:
    """Inspect public source references and open verified links."""

    def __init__(self, frame, requested_source):
        from orbitoby._easy_sources import source_table

        self._table = source_table(frame)
        self.requested_source = requested_source

    @property
    def table(self):
        return self._table.copy()

    def show(self):
        if self._table.empty:
            print("No source records were found.")
        else:
            print(self._table.to_string(index=False))
        return self

    def open(self, which=None):
        """Open a public source page at the user's request."""
        import webbrowser

        selected = self._table

        if which is not None:
            if not isinstance(which, str) or not which.strip():
                raise ValueError("Choose a metric or provider name.")

            key = which.strip().casefold()

            matches = (
                selected["metric"].str.casefold().eq(key)
                | selected["source"].str.casefold().eq(key)
                | selected["dataset"].str.casefold().eq(key)
            )

            selected = selected.loc[matches]

        links = set()

        for _, row in selected.iterrows():
            url = row["data_page"] or row["provider_site"]
            if url:
                links.add(url)

        if not links:
            raise ValueError("No verified public link is available for this source.")

        if len(links) != 1:
            raise ValueError(
                "Multiple source pages exist. Choose one, "
                'for example: result.sources().open("Kp")'
            )

        url = links.pop()
        webbrowser.open(url)
        return url


class DataResult:
    """Wrap a Core DataFrame without altering its data."""

    def __init__(self, frame, *, name, start, end, source):
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("Expected a pandas DataFrame.")

        self._raw_artifact_ids = ()
        self._frame = frame
        self.name = name
        self.start = start
        self.end = end
        self.requested_source = source

    @property
    def table(self):
        return self._frame.copy()

    def show(self, rows=10):
        if rows < 1:
            raise ValueError("rows must be positive.")

        preview = self._frame.head(rows)

        try:
            from IPython.display import display
        except ImportError:
            print(preview.to_string(index=False))
        else:
            display(preview)

        return self

    @property
    def provenance(self):
        """Verified request-level raw lineage, when available."""
        return pd.DataFrame(
            [
                {
                    "artifact_id": artifact_id,
                    "lineage_level": "raw_request",
                    "requested_source": self.requested_source,
                }
                for artifact_id in self._raw_artifact_ids
            ],
            columns=[
                "artifact_id",
                "lineage_level",
                "requested_source",
            ],
        )

    def artifacts(self):
        """List only verified raw artifacts contributing to this result."""
        from orbitoby._easy_lineage import result_artifacts

        return result_artifacts(self)

    def records(self):
        """List only provider records linked by exact record IDs."""
        from orbitoby._easy_lineage import result_records

        return result_records(self)

    def coverage(self):
        """Inspect actual UTC record times without invented coverage ratios."""
        from orbitoby._easy_coverage import result_coverage

        return result_coverage(self)

    def change(self, field=None, **options):
        """Calculate differences or rates at actual observed epochs."""
        from orbitoby._easy_change import change_result

        return change_result(self, field, **options)

    def info(self, topic=None):
        if topic is not None:
            if not isinstance(topic, str) or not topic.strip():
                raise ValueError("info topic must be a non-empty string.")

            topic = topic.strip().lower()

            if topic in ("artifacts", "records", "coverage"):
                getattr(self, topic)().show()
                return self

            if topic == "license":
                print(
                    "A license is not automatically established "
                    "by the requested provider name."
                )
                print(
                    "Inspect result.sources().show() and "
                    "ob.licenses().show() for declared terms."
                )
                return self

            if topic == "provenance":
                evidence = getattr(self, "provenance", None)
                if isinstance(evidence, pd.DataFrame):
                    print("Provenance rows:", len(evidence))
                else:
                    print("No row-level provenance table is available.")
                print("Use info('artifacts') for verified raw links.")
                return self

            if topic == "debug":
                print("Result class:", type(self).__name__)
                print("Row count:", len(self._frame))
                print("Requested provider:", self.requested_source)
                print("Sensitive request values are not shown.")
                return self

            raise ValueError(
                "Unknown info topic. Choose artifacts, records, "
                "coverage, license, provenance or debug."
            )

        print(f"Data: {self.name}")
        print(f"Period: {self.start} to {self.end} (end excluded)")
        print(f"Rows: {len(self._frame)}")
        print(f"Requested provider: {self.requested_source}")
        print("Time convention: UTC [start, end)")
        print("Interpolation by Easy API: None")
        print("Resampling by Easy API: None")
        print("Source details: use result.sources().show()")
        return self

    def plot(self, *, kind="auto", title=None, width=900, height=360, below=None):
        """Create an SVG plot with its original data sources."""
        from orbitoby._easy_plot import plot_result

        return plot_result(
            self,
            kind=kind,
            title=title,
            width=width,
            height=height,
            below=below,
        )

    def compare(self, other):
        """Compare matching physical quantities at exact UTC times."""
        from orbitoby._easy_compare import ComparisonResult

        return ComparisonResult(self, other)

    def sources(self):
        return SourceList(self._frame, self.requested_source)

    def save(self, filename):
        path = Path(filename)

        if path.suffix.lower() != ".csv":
            raise ValueError("For now, use a .csv filename.")

        from orbitoby._easy_export import export_result_csv

        return export_result_csv(self, path)


class WindowResult(DataResult):
    """Exact-time aligned data with its original scientific metadata."""

    def __init__(self, window, *, name, start, end, source):
        from orbitoby.research import ResearchWindow

        if not isinstance(window, ResearchWindow):
            raise TypeError("Expected an Orbitoby ResearchWindow.")

        self._window = window
        super().__init__(
            window.data,
            name=name,
            start=start,
            end=end,
            source=source,
        )

    @property
    def provenance(self):
        return self._window.provenance.copy()

    @property
    def presence(self):
        return self._window.presence.copy()

    @property
    def missing_reason(self):
        return self._window.missing_reason.copy()

    @property
    def units(self):
        return dict(self._window.units)

    def sources(self):
        return SourceList(
            self._window.provenance,
            self.requested_source,
        )

    def info(self, topic=None):
        if topic is not None:
            return super().info(topic)

        super().info()
        print("Alignment: exact timestamp union")
        print("Interpolation: none")
        print("Resampling: none")
        print("Units:", self.units)
        self.sources().show()
        return self

    def save(self, filename):
        import json

        path = super().save(filename)

        # Export the scientific metadata separately.
        # Raw context is not exported because it may contain private URLs.
        safe_columns = [
            "timestamp",
            "metric",
            "source",
            "dataset",
            "source_field",
            "source_version",
            "unit",
            "artifact_id",
            "retrieved_at",
            "method",
            "transform",
            "transform_version",
            "missing_reason",
        ]

        provenance = self._window.provenance
        columns = [c for c in safe_columns if c in provenance.columns]

        provenance[columns].to_csv(
            path.with_name(path.stem + "_provenance.csv"),
            index=False,
        )

        self._window.presence.to_csv(
            path.with_name(path.stem + "_presence.csv"),
            index=False,
        )

        self._window.missing_reason.to_csv(
            path.with_name(path.stem + "_missing.csv"),
            index=False,
        )

        metadata = {
            "units": self.units,
            "time_convention": "UTC [start, end)",
            "alignment": "exact timestamp union",
            "interpolation": "none",
            "resampling": "none",
            "provenance_export": "selected safe fields",
        }

        path.with_name(path.stem + "_metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return path


class SatelliteResult(DataResult):
    """Space-object candidates that can be selected by NORAD ID."""

    def pick(self, *norad_ids):
        from numbers import Integral

        if not norad_ids:
            raise ValueError("Choose a NORAD ID, e.g. satellites.pick(39452).")

        if any(
            isinstance(value, bool) or not isinstance(value, Integral) or value <= 0
            for value in norad_ids
        ):
            raise ValueError("NORAD IDs must be positive integers.")

        ids = [int(value) for value in norad_ids]

        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate NORAD IDs are not allowed.")

        if "norad_id" not in self._frame.columns:
            raise ValueError("This table does not contain NORAD IDs.")

        if self._frame["norad_id"].duplicated().any():
            raise ValueError("Candidate table contains duplicate NORAD IDs.")

        available = set(self._frame["norad_id"].dropna().astype(int))
        missing = sorted(set(ids) - available)

        if missing:
            raise ValueError(f"NORAD IDs not in these candidates: {missing}")

        selected = (
            self._frame.set_index("norad_id", drop=False)
            .loc[ids]
            .reset_index(drop=True)
        )

        return SatelliteResult(
            selected,
            name="selected satellites",
            start=self.start,
            end=self.end,
            source=self.requested_source,
        )


class OrbitResult(DataResult):
    """Historical orbital records with explicit screening."""

    def __init__(self, frame, *, name, start, end, source, archive, norad_ids):
        super().__init__(frame, name=name, start=start, end=end, source=source)
        self._archive = archive
        self._norad_ids = tuple(norad_ids)

    def plot(
        self,
        field="periapsis",
        *,
        kind="scatter",
        title=None,
        width=900,
        height=360,
    ):
        """Plot original orbital-element epochs, separated by NORAD ID."""
        from orbitoby._easy_orbit_plot import plot_orbit

        return plot_orbit(
            self,
            field,
            kind=kind,
            title=title,
            width=width,
            height=height,
        )

    def check(
        self,
        *,
        altitude=None,
        coverage=None,
        periapsis=None,
        apoapsis=None,
        inclination=None,
        eccentricity=None,
        mean_motion=None,
        orbit_match="all",
    ):
        if altitude is not None and periapsis is not None:
            raise ValueError("Use either altitude or periapsis, not both.")

        periapsis_range = altitude if altitude is not None else periapsis

        options = {
            "periapsis_km": periapsis_range,
            "apoapsis_km": apoapsis,
            "inclination_deg": inclination,
            "eccentricity": eccentricity,
            "mean_motion": mean_motion,
            "min_coverage": coverage,
            "orbit_match": orbit_match,
        }

        frame = self._archive.orbit_summary(
            self._norad_ids,
            start=self.start,
            end=self.end,
            source=self.requested_source,
            sync=False,
            **options,
        )

        return OrbitCheckResult(
            frame,
            name="historical orbit screening",
            start=self.start,
            end=self.end,
            source=self.requested_source,
            criteria=options,
        )


class OrbitCheckResult(DataResult):
    """Screening decisions, retaining failed candidates and reasons."""

    def __init__(self, frame, *, criteria, **kwargs):
        super().__init__(frame, **kwargs)
        self.criteria = dict(criteria)

    def info(self):
        super().info()
        print("Altitude: periapsis height in km")
        print("Coverage: fraction of UTC days containing orbit records")
        print("Screening does not modify original orbit records.")
        print("Conditions:")
        for key, value in self.criteria.items():
            if value is not None:
                print(f"  {key}: {value}")
        return self

    def passed(self):
        if "matches" not in self._frame.columns:
            raise ValueError("Screening result has no matches column.")

        passed = self._frame.loc[self._frame["matches"].eq(True)].copy()

        return SatelliteResult(
            passed,
            name="satellites passing orbit screening",
            start=self.start,
            end=self.end,
            source=self.requested_source,
        )
