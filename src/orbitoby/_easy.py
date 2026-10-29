"""Beginner-friendly Orbitoby API."""

from datetime import date, datetime


def _parse_day(value, name):
    if isinstance(value, datetime):
        raise TypeError(f"{name}: use a date, not a datetime.")

    if isinstance(value, date):
        return value

    if not isinstance(value, str):
        raise TypeError(f"{name}: use YYYY-MM-DD.")

    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError
        return parsed
    except ValueError as exc:
        raise ValueError(f"{name}: expected YYYY-MM-DD, got {value!r}.") from exc


class Study:
    """A research period in UTC, with an exclusive end date."""

    def __init__(self, start, end):
        self.start = _parse_day(start, "start")
        self.end = _parse_day(end, "end")

        if self.start >= self.end:
            raise ValueError("The end date must be after the start date.")

        self._archive = None
        self._closed = False

    @property
    def _core(self):
        if self._closed:
            raise RuntimeError("This study is closed.")

        if self._archive is None:
            from orbitoby._easy_login import shared_credentials
            from orbitoby.service import Archive

            self._archive = Archive(credentials=shared_credentials())

        return self._archive

    def weather(self, *names, source=None):
        """Get one or more space-weather quantities."""
        from orbitoby._easy_result import DataResult, WindowResult

        aliases = {
            "kp": ("kp", "gfz"),
            "dst": ("dst", "wdc_kyoto"),
            "f10.7": ("f107_observed", "gfz"),
            "f107": ("f107_observed", "gfz"),
        }

        if not names:
            raise ValueError('Choose data, for example: study.weather("Kp")')

        selected = []

        for name in names:
            key = name.strip().lower() if isinstance(name, str) else ""

            if key not in aliases:
                raise ValueError(
                    f"Unknown weather data: {name!r}. Try Kp, Dst or F10.7."
                )

            selected.append(aliases[key])

        metrics = [item[0] for item in selected]

        if len(set(metrics)) != len(metrics):
            raise ValueError("The same weather data was requested twice.")

        if source is not None:
            if not isinstance(source, str) or not source.strip():
                raise ValueError("source must be a provider name.")
            chosen_source = source.strip().lower()
        else:
            chosen_source = None

        if len(metrics) == 1:
            metric, recommended = selected[0]
            provider = chosen_source or recommended

            frame = self._core.space_weather(
                start=self.start,
                end=self.end,
                fields=metric,
                source=provider,
            )

            from orbitoby._easy_lineage import verified_scientific_artifact_ids

            result = DataResult(
                frame,
                name=metric,
                start=self.start,
                end=self.end,
                source=provider,
            )

            result._raw_artifact_ids = verified_scientific_artifact_ids(
                self._core,
                frame,
            )
            return result

        recommended = tuple(dict.fromkeys(provider for _, provider in selected))

        options = {
            "start": self.start,
            "end": self.end,
            "fields": tuple(metrics),
        }

        if chosen_source is not None:
            options["source"] = chosen_source
        else:
            options["source_preference"] = recommended

        window = self._core.window(**options)

        provenance = window.provenance

        for metric, recommended_source in selected:
            expected = chosen_source or recommended_source

            actual = set(
                provenance.loc[provenance["metric"] == metric, "source"]
                .dropna()
                .astype(str)
            )

            if actual and actual != {expected}:
                raise ValueError(
                    f"{metric}: unexpected source {sorted(actual)}. "
                    f"Expected {expected}. Nothing was silently mixed."
                )

        return WindowResult(
            window,
            name=", ".join(metrics),
            start=self.start,
            end=self.end,
            source=chosen_source or "recommended",
        )

    def objects(
        self,
        *,
        type=None,
        existence="throughout",
        sync=True,
        limit=None,
    ):
        """Find space objects associated with the study period."""
        from orbitoby._easy_result import DataResult

        if existence not in ("throughout", "overlap"):
            raise ValueError("existence must be 'throughout' or 'overlap'.")

        if type is not None and (not isinstance(type, str) or not type.strip()):
            raise ValueError("type must be a non-empty object type.")

        if not isinstance(sync, bool):
            raise TypeError("sync must be True or False.")

        frame = self._core.objects(
            start=self.start,
            end=self.end,
            existence=existence,
            object_type=type,
            sync=sync,
            limit=limit,
        )

        return DataResult(
            frame,
            name=type or "space objects",
            start=self.start,
            end=self.end,
            source="celestrak",
        )

    def satellites(
        self,
        *,
        existence="throughout",
        sync=True,
        limit=None,
    ):
        """Find payloads existing during the study period."""
        from orbitoby._easy_result import SatelliteResult

        result = self.objects(
            type="payload",
            existence=existence,
            sync=sync,
            limit=limit,
        )

        return SatelliteResult(
            result.table,
            name="satellites",
            start=self.start,
            end=self.end,
            source=result.requested_source,
        )

    def swarm(self, satellite):
        """Select Swarm A, B or C without fetching data."""
        from orbitoby._easy_swarm import Swarm

        return Swarm(self, satellite)

    def orbit(self, *norad_ids, source="spacetrack", sync=True):
        """Get historical orbital elements for one or more NORAD IDs."""
        from numbers import Integral

        import pandas as pd

        from orbitoby._easy_result import OrbitResult, SatelliteResult

        if len(norad_ids) == 1 and isinstance(norad_ids[0], SatelliteResult):
            norad_ids = tuple(norad_ids[0].table["norad_id"].tolist())

        if not norad_ids:
            raise ValueError("Enter a NORAD ID, for example: study.orbit(39452)")

        for norad_id in norad_ids:
            if (
                isinstance(norad_id, bool)
                or not isinstance(norad_id, Integral)
                or norad_id <= 0
            ):
                raise ValueError(
                    f"Invalid NORAD ID: {norad_id!r}. "
                    "Use a positive integer such as 39452."
                )

        if len(set(norad_ids)) != len(norad_ids):
            raise ValueError("Duplicate NORAD IDs were provided.")

        if not isinstance(source, str):
            raise TypeError("source must be a provider name.")

        source_name = source.strip().lower()
        if source_name == "space-track":
            source_name = "spacetrack"

        frames = []

        for norad_id in norad_ids:
            try:
                frame = self._core.orbit(
                    norad_id=int(norad_id),
                    start=self.start,
                    end=self.end,
                    source=source_name,
                    sync=sync,
                )
            except Exception as exc:
                raise RuntimeError(
                    f"Could not retrieve historical orbit for "
                    f"NORAD {norad_id}. "
                    "Check credentials, provider access and coverage."
                ) from exc

            if not isinstance(frame, pd.DataFrame):
                raise TypeError("The Core orbit API did not return a DataFrame.")

            # Core orbital epochs represent UTC instants.
            # DuckDB may return timezone-naive timestamps.
            # Normalize only at this trusted orbital-data boundary.
            if "epoch" in frame.columns and not frame.empty:
                frame = frame.copy(deep=True)
                frame["epoch"] = pd.to_datetime(
                    frame["epoch"],
                    errors="raise",
                    utc=True,
                )

            if "norad_id" not in frame.columns:
                frame = frame.assign(norad_id=int(norad_id))

            frames.append(frame)

        combined = pd.concat(frames, ignore_index=True)

        from orbitoby._easy_lineage import verified_orbit_artifact_ids

        result = OrbitResult(
            combined,
            name="historical orbit",
            start=self.start,
            end=self.end,
            source=source_name,
            archive=self._core,
            norad_ids=tuple(int(value) for value in norad_ids),
        )

        result._raw_artifact_ids = verified_orbit_artifact_ids(
            self._core,
            combined,
        )
        return result

    def msis_inputs(
        self,
        satellite=None,
        *,
        product="pod",
        source="gfz",
        trajectory=None,
    ):
        """Prepare explicit NRLMSIS forcing without model calculation."""
        from orbitoby._easy_msis import MsisInputsResult
        from orbitoby._easy_trajectory import TrajectoryResult

        if not isinstance(source, str) or source.strip().lower() != "gfz":
            raise ValueError("NRLMSIS forcing currently requires source='GFZ'.")

        if trajectory is None:
            if satellite is None:
                raise ValueError('Select a spacecraft: study.msis_inputs("A")')
            trajectory = self.swarm(satellite).trajectory(product=product)
        elif satellite is not None:
            raise ValueError("Provide a satellite OR a trajectory, not both.")

        if not isinstance(trajectory, TrajectoryResult):
            raise TypeError(
                'Use a Swarm trajectory returned by study.swarm("A").trajectory().'
            )

        if trajectory.start != self.start or trajectory.end != self.end:
            raise ValueError("Trajectory and study periods must match.")

        frame, lineage = self._core.msis_inputs(
            trajectory.table,
            driver_source="gfz",
            trajectory_parents=trajectory.parents,
        )

        return MsisInputsResult(
            frame,
            trajectory=trajectory,
            lineage=lineage,
            driver_source="gfz",
        )

    def msis(
        self,
        satellite=None,
        *,
        product="pod",
        source="gfz",
        trajectory=None,
        inputs=None,
    ):
        """Calculate NRLMSIS 2.1 on an actual Swarm trajectory."""
        import pandas as pd

        from orbitoby._easy_msis import MsisInputsResult, MsisResult

        if inputs is None:
            inputs = self.msis_inputs(
                satellite,
                product=product,
                source=source,
                trajectory=trajectory,
            )
        elif satellite is not None or trajectory is not None:
            raise ValueError("Provide inputs OR satellite/trajectory, not both.")

        if not isinstance(inputs, MsisInputsResult):
            raise TypeError('Use inputs returned by study.msis_inputs("A").')

        if inputs.start != self.start or inputs.end != self.end:
            raise ValueError("Model inputs and study periods must match.")

        try:
            frame = self._core.msis_density(
                inputs.table,
                parents=inputs.lineage,
            )
        except ImportError as exc:
            raise ImportError(
                'Install the model extra: pip install "orbitoby[models]"'
            ) from exc

        if not isinstance(frame, pd.DataFrame):
            raise TypeError("NRLMSIS Core did not return a DataFrame.")

        if not frame.empty:
            if (
                "artifact_kind" not in frame
                or not frame["artifact_kind"].eq("model_output").all()
            ):
                raise ValueError("NRLMSIS output has invalid model/observation role.")

            if (
                "dataset" not in frame
                or not frame["dataset"].eq("nrlmsis_2_1_density").all()
            ):
                raise ValueError("Unexpected NRLMSIS model dataset.")

        return MsisResult(frame, inputs=inputs)

    def data(self, name, source=None, dataset=None, **native_options):
        """Retrieve registered provider records without reinterpretation."""
        from orbitoby._easy_native import fetch_data

        return fetch_data(
            self,
            name,
            source=source,
            dataset=dataset,
            **native_options,
        )

    def object(self, id=None, *, norad_id=None, cospar_id=None, object_id=None):
        """Inspect one locally indexed object and its provider records."""
        from orbitoby._easy_identity import ObjectResult

        if id is not None:
            if any(value is not None for value in (norad_id, cospar_id, object_id)):
                raise ValueError(
                    "Use either a positional NORAD ID or explicit "
                    "identifier keywords, not both."
                )

            if isinstance(id, bool) or not isinstance(id, int) or id <= 0:
                raise ValueError(
                    "A positional object ID must be a positive NORAD integer."
                )

            norad_id = id

        if all(value is None for value in (norad_id, cospar_id, object_id)):
            raise ValueError("Specify a NORAD, COSPAR or internal object ID.")

        record = self._core.object(
            norad_id=norad_id,
            cospar_id=cospar_id,
            object_id=object_id,
        )

        if record is None:
            raise LookupError(
                "The object was not found in the local index. "
                "This does not establish that it never existed."
            )

        return ObjectResult(record)

    def search(
        self,
        query=None,
        *,
        norad_id=None,
        cospar_id=None,
        source=None,
        dataset=None,
        properties=None,
        limit=100,
        offset=0,
    ):
        """Search locally indexed objects without a network request."""
        import pandas as pd

        from orbitoby._easy_identity import SearchResult

        if query is not None and (not isinstance(query, str) or not query.strip()):
            raise ValueError("Search text must be a non-empty string.")

        for key, value in (("limit", limit), ("offset", offset)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{key} must be a nonnegative integer.")

        frame = self._core.search(
            name=query,
            norad_id=norad_id,
            cospar_id=cospar_id,
            source=source,
            dataset=dataset,
            properties=properties,
            limit=limit,
            offset=offset,
        )

        if not isinstance(frame, pd.DataFrame):
            raise TypeError("Core search() did not return a DataFrame.")

        return SearchResult(frame)

    def compare(self, first, second, **options):
        """Compare two results using the existing scientific comparison."""
        if options:
            names = ", ".join(sorted(options))
            raise TypeError(
                f"Unsupported comparison options: {names}. "
                "Use study.compare(first, second) for exact-time "
                "comparison without invented interpolation."
            )

        compare_method = getattr(first, "compare", None)

        if not callable(compare_method):
            raise TypeError(
                "The first argument must be an Orbitoby result supporting compare()."
            )

        return compare_method(second)

    def align(self, *results):
        """Align results on exact UTC times without interpolation."""
        from orbitoby._easy_align import align_results

        return align_results(*results)

    def close(self):
        if not self._closed:
            self._closed = True
            if self._archive is not None:
                self._archive.close()
                self._archive = None

    def __repr__(self):
        return f"Study({self.start!s}, {self.end!s}, UTC, end excluded)"

    # Science Day v0.2 progressive API: same study context, optional controls.
    def catalog(self, group="all", *, refresh=False):
        """Explore satellite identities. Snapshot membership is not period coverage."""
        from ._science_day import catalog

        return catalog(group, refresh=refresh)

    def solar(self, metric, *, refresh=False):
        """Get official long-span solar/geomagnetic data for this study period."""
        from ._science_day import solar_history

        return solar_history(metric, self.start, self.end, refresh=refresh)


def study(start, end):
    """Start a study using two dates."""
    return Study(start, end)
