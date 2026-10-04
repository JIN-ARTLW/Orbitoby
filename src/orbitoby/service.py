from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta
from typing import Any, Self

import pandas as pd

from orbitoby.archive.raw import (
    RawArtifact,
    save_raw_artifact,
)
from orbitoby.auth import CredentialManager
from orbitoby.catalogue import CatalogueAPI
from orbitoby.models.msis import (
    DATASET as MSIS_DATASET,
)
from orbitoby.models.msis import (
    METHOD as MSIS_METHOD,
)
from orbitoby.models.msis import (
    METRIC as MSIS_METRIC,
)
from orbitoby.models.msis import (
    TRANSFORM as MSIS_TRANSFORM,
)
from orbitoby.models.msis import (
    TRANSFORM_VERSION as MSIS_TRANSFORM_VERSION,
)
from orbitoby.models.msis import (
    UNIT as MSIS_UNIT,
)
from orbitoby.models.msis import (
    calculate_msis_density,
)
from orbitoby.plotting import PlotAPI
from orbitoby.research import ResearchAPI
from orbitoby.source_api import SourceAPI
from orbitoby.sources.base import SourceAdapter
from orbitoby.sources.registry import build_sources
from orbitoby.warehouse.coverage import missing_ranges
from orbitoby.warehouse.db import connect_db
from orbitoby.warehouse.identity import IdentityStore
from orbitoby.warehouse.products import (
    ProductParent,
    ProductStore,
)
from orbitoby.warehouse.scientific import ScientificStore


class Archive(CatalogueAPI, SourceAPI, PlotAPI, ResearchAPI):
    """
    Orbitoby의 메인 서비스.

    역할
    ----
    1. 외부 데이터 소스 관리
    2. 원하는 데이터 조회
    3. 기존 coverage 확인
    4. 부족한 기간만 추가 다운로드
    5. API 원본(raw) 영구 보존
    6. source별 데이터를 내부 형식으로 정규화
    7. DuckDB 저장 및 조회
    8. DataFrame 형태로 사용자에게 반환
    """

    def __init__(
        self,
        *,
        credentials: CredentialManager | None = None,
        allow_dotenv: bool = False,
    ) -> None:
        self.con = connect_db()

        self.scientific_store = ScientificStore(self.con)

        self.product_store = ProductStore(self.con)

        self.credentials = credentials or CredentialManager(
            allow_dotenv=allow_dotenv,
        )

        self.sources: dict[str, SourceAdapter] = build_sources(
            credentials=self.credentials
        )

    # ==================================================================
    # General helpers
    # ==================================================================

    @staticmethod
    def _parse_date(
        value: str | date,
    ) -> date:
        """
        YYYY-MM-DD 문자열 또는 date 객체를
        date 객체로 통일한다.
        """

        if isinstance(value, date):
            return value

        return date.fromisoformat(value)

    def get_source(
        self,
        name: str,
    ) -> SourceAdapter:
        """
        등록된 source adapter를 반환한다.
        """

        try:
            return self.sources[name]

        except KeyError as exc:
            available = ", ".join(sorted(self.sources))

            raise ValueError(
                f"Unknown source: {name}. Available sources: {available}"
            ) from exc

    def sources_available(
        self,
    ) -> list[str]:
        """
        현재 Archive에 등록된 데이터 소스 이름 목록.
        """

        return sorted(self.sources.keys())

    # ==================================================================
    # Generic source fetch
    # ==================================================================

    def _fetch_records(
        self,
        *,
        source: str,
        dataset: str,
        archive_raw: bool = True,
        **params: Any,
    ) -> tuple[
        list[dict],
        RawArtifact | None,
    ]:
        """Fetch provider data and retain raw provenance."""

        for key in ("start", "end"):
            if params.get(key) is not None:
                params[key] = self._parse_date(params[key])

        adapter = self.get_source(source)

        payload = adapter.fetch(
            dataset,
            **params,
        )

        artifact = None

        if archive_raw:
            artifact = save_raw_artifact(
                source=source,
                dataset=dataset,
                payload=payload,
                norad_id=params.get("norad_id"),
                start=params.get("start"),
                end=params.get("end"),
                metadata={"params": {key: str(value) for key, value in params.items()}},
                extension=adapter.raw_extension_for(
                    dataset,
                    **params,
                ),
            )

            self._register_artifact(artifact)

        records = adapter.normalize(
            dataset,
            payload,
            **params,
        )

        if artifact is not None and adapter.should_index_identity_request(
            dataset,
            **params,
        ):
            index_params = {
                key: value
                for key, value in params.items()
                if key
                not in {
                    "limit",
                    "local_limit",
                }
            }

            indexed_records = adapter.normalize(
                dataset,
                payload,
                **index_params,
            )

            IdentityStore(self.con).ingest(
                indexed_records,
                artifact,
            )

        return records, artifact

    def fetch(
        self,
        *,
        source: str,
        dataset: str,
        archive_raw: bool = True,
        **params: Any,
    ) -> pd.DataFrame:
        """Low-level provider-specific data query."""

        records, _ = self._fetch_records(
            source=source,
            dataset=dataset,
            archive_raw=archive_raw,
            **params,
        )

        return pd.DataFrame(records)

    # ==================================================================
    # Historical orbit
    # ==================================================================

    def orbit(
        self,
        *,
        norad_id: int,
        start: str | date,
        end: str | date,
        source: str = "spacetrack",
        sync: bool = True,
    ) -> pd.DataFrame:
        """
        특정 우주물체의 historical orbital elements를 조회한다.

        현재 historical orbit archive의 기본 source는
        Space-Track GP_HISTORY이다.

        Parameters
        ----------
        norad_id:
            NORAD Catalog ID.

        start:
            시작 날짜.

        end:
            종료 날짜.

        source:
            historical orbit source.
            현재는 spacetrack 지원.

        sync:
            True:
                로컬 archive에 없는 기간을 자동 다운로드.

            False:
                네트워크 요청 없이 기존 DuckDB 데이터만 조회.
        """

        start_date = self._parse_date(start)

        end_date = self._parse_date(end)

        if start_date >= end_date:
            raise ValueError("start must be before end")

        inclusive_end = end_date - timedelta(days=1)

        if source != "spacetrack":
            raise ValueError(
                "Historical orbit synchronization currently "
                "supports source='spacetrack' only."
            )

        # --------------------------------------------------------------
        # 필요한 기간 중 아직 없는 구간 탐색
        # --------------------------------------------------------------

        if sync:
            gaps = missing_ranges(
                self.con,
                source=source,
                dataset="gp_history",
                norad_id=norad_id,
                start=start_date,
                end=inclusive_end,
            )

            for gap_start, gap_end in gaps:
                self._sync_gp_history(
                    source_name=source,
                    norad_id=norad_id,
                    start=gap_start,
                    end=gap_end,
                )

        # --------------------------------------------------------------
        # DuckDB에서 요청 기간 반환
        # --------------------------------------------------------------

        return self.con.execute(
            """
            SELECT *
            FROM orbit_elements
            WHERE norad_id = ?
              AND source = ?
              AND epoch >= ?
              AND epoch < ?
            ORDER BY epoch
            """,
            [
                norad_id,
                source,
                start_date,
                end_date,
            ],
        ).df()

    def orbit_summary(
        self,
        objects,
        *,
        start: str | date,
        end: str | date,
        periapsis_km=None,
        apoapsis_km=None,
        inclination_deg=None,
        eccentricity=None,
        mean_motion=None,
        min_coverage: float | None = None,
        orbit_match: str = "all",
        source: str = "spacetrack",
        sync: bool = False,
    ) -> pd.DataFrame:
        """Summarize historical orbit records for multiple objects.

        ``objects`` may be:

        - a DataFrame containing ``norad_id``;
        - an iterable of NORAD catalogue IDs.

        The requested interval follows Orbitoby's public
        half-open convention: [start, end).

        Numeric range filters are inclusive ``(minimum, maximum)``
        pairs. No interpolation, smoothing, resampling, filling,
        or implicit conflict resolution occurs.

        ``orbit_match="all"`` requires every usable historical
        record to satisfy all requested orbital ranges.

        ``orbit_match="any"`` requires at least one historical
        record to satisfy all requested orbital ranges.

        ``min_coverage`` is the minimum fraction of requested UTC
        calendar dates containing at least one historical orbit
        record. It is derived from actual stored records, not from
        provider-request success or the coverage request ledger.

        Per-object retrieval failures are retained in the returned
        table instead of aborting the entire population query.
        """

        start_date = self._parse_date(start)
        end_date = self._parse_date(end)

        if start_date >= end_date:
            raise ValueError("start must be before end")

        if not isinstance(sync, bool):
            raise TypeError("sync must be a boolean")

        if orbit_match not in {
            "all",
            "any",
        }:
            raise ValueError("orbit_match must be 'all' or 'any'")

        if min_coverage is not None:
            if isinstance(min_coverage, bool) or not isinstance(
                min_coverage,
                (int, float),
            ):
                raise TypeError("min_coverage must be a number between 0 and 1")

            min_coverage = float(min_coverage)

            if not (0.0 <= min_coverage <= 1.0):
                raise ValueError("min_coverage must be between 0 and 1")

        def normalize_range(
            name,
            value,
        ):
            if value is None:
                return None

            if (
                not isinstance(
                    value,
                    (tuple, list),
                )
                or len(value) != 2
            ):
                raise TypeError(f"{name} must be a (minimum, maximum) pair")

            result = []

            for item in value:
                if isinstance(item, bool) or not isinstance(
                    item,
                    (int, float),
                ):
                    raise TypeError(f"{name} bounds must be numeric")

                number = float(item)

                if pd.isna(number) or number in {
                    float("inf"),
                    float("-inf"),
                }:
                    raise ValueError(f"{name} bounds must be finite")

                result.append(number)

            lower, upper = result

            if lower > upper:
                raise ValueError(f"{name} minimum must not exceed maximum")

            return lower, upper

        ranges = {
            "periapsis_km": normalize_range(
                "periapsis_km",
                periapsis_km,
            ),
            "apoapsis_km": normalize_range(
                "apoapsis_km",
                apoapsis_km,
            ),
            "inclination_deg": normalize_range(
                "inclination_deg",
                inclination_deg,
            ),
            "eccentricity": normalize_range(
                "eccentricity",
                eccentricity,
            ),
            "mean_motion": normalize_range(
                "mean_motion",
                mean_motion,
            ),
        }

        active_ranges = {
            key: value for key, value in ranges.items() if value is not None
        }

        if isinstance(
            objects,
            pd.DataFrame,
        ):
            if "norad_id" not in objects.columns:
                raise ValueError("objects DataFrame must contain 'norad_id'")

            candidate_rows = objects.to_dict("records")

        else:
            if isinstance(
                objects,
                (str, bytes),
            ):
                raise TypeError("objects must be a DataFrame or iterable of NORAD IDs")

            try:
                candidate_rows = [
                    {
                        "norad_id": value,
                    }
                    for value in objects
                ]
            except TypeError as exc:
                raise TypeError(
                    "objects must be a DataFrame or iterable of NORAD IDs"
                ) from exc

        def normalize_norad_id(
            value,
        ) -> int:
            if pd.isna(value):
                raise ValueError("NORAD ID must not be missing")

            if hasattr(value, "item"):
                try:
                    value = value.item()
                except ValueError:
                    pass

            if isinstance(value, bool):
                raise TypeError("NORAD ID must not be a boolean")

            if isinstance(value, float):
                if not value.is_integer():
                    raise ValueError(f"Invalid NORAD ID: {value!r}")

                value = int(value)

            text_value = str(value).strip()

            if not text_value.isdigit() or len(text_value) > 9 or int(text_value) <= 0:
                raise ValueError(f"Invalid NORAD ID: {value!r}")

            return int(text_value)

        def clean_metadata(
            value,
        ):
            if value is None:
                return None

            try:
                if pd.isna(value):
                    return None
            except (
                TypeError,
                ValueError,
            ):
                pass

            return value

        candidates = []
        seen = set()

        for candidate in candidate_rows:
            norad_id = normalize_norad_id(candidate.get("norad_id"))

            if norad_id in seen:
                continue

            seen.add(norad_id)

            candidates.append(
                {
                    "norad_id": norad_id,
                    "object_id": clean_metadata(candidate.get("object_id")),
                    "cospar_id": clean_metadata(candidate.get("cospar_id")),
                    "name": clean_metadata(candidate.get("name")),
                }
            )

        start_ts = pd.Timestamp(
            start_date,
            tz="UTC",
        )

        end_ts = pd.Timestamp(
            end_date,
            tz="UTC",
        )

        requested_days = (end_date - start_date).days

        requested_seconds = (end_ts - start_ts).total_seconds()

        summary_fields = (
            "periapsis_km",
            "apoapsis_km",
            "inclination_deg",
            "eccentricity",
            "mean_motion",
        )

        output = []

        for candidate in candidates:
            base = {
                **candidate,
                "requested_start": start_date,
                "requested_end": end_date,
                "orbit_source": source,
                "orbit_rows": 0,
                "orbit_days": 0,
                "observed_day_ratio": 0.0,
                "first_epoch": None,
                "last_epoch": None,
                "epoch_span_ratio": 0.0,
                "median_gap_hours": None,
                "max_gap_hours": None,
                "artifact_count": 0,
                "artifact_ids": (),
            }

            for field in summary_fields:
                base[f"{field}_min"] = None
                base[f"{field}_median"] = None
                base[f"{field}_max"] = None

            base["matches"] = False
            base["filter_reason"] = None
            base["error"] = None

            try:
                frame = self.orbit(
                    norad_id=(candidate["norad_id"]),
                    start=start_date,
                    end=end_date,
                    source=source,
                    sync=sync,
                )

            except Exception as exc:  # noqa: BLE001
                base["filter_reason"] = "fetch_error"

                base["error"] = f"{type(exc).__name__}: {exc}"

                output.append(base)
                continue

            if frame.empty:
                base["filter_reason"] = "no_orbit_records"

                output.append(base)
                continue

            if "epoch" not in frame.columns:
                base["filter_reason"] = "missing_epoch"

                base["error"] = "Orbit data has no epoch column."

                output.append(base)
                continue

            try:
                epochs = pd.to_datetime(
                    frame["epoch"],
                    utc=True,
                    errors="raise",
                )

            except Exception as exc:  # noqa: BLE001
                base["filter_reason"] = "invalid_epoch"

                base["error"] = f"{type(exc).__name__}: {exc}"

                output.append(base)
                continue

            in_window = (epochs >= start_ts) & (epochs < end_ts)

            frame = frame.loc[in_window].copy()

            epochs = epochs.loc[in_window]

            if frame.empty:
                base["filter_reason"] = "no_orbit_records"

                output.append(base)
                continue

            frame["_orbitoby_epoch"] = epochs

            frame = frame.sort_values("_orbitoby_epoch").reset_index(drop=True)

            epochs = frame["_orbitoby_epoch"]

            base["orbit_rows"] = len(frame)

            observed_days = int(epochs.dt.floor("D").nunique())

            base["orbit_days"] = observed_days

            base["observed_day_ratio"] = observed_days / requested_days

            first_epoch = epochs.iloc[0]
            last_epoch = epochs.iloc[-1]

            base["first_epoch"] = first_epoch

            base["last_epoch"] = last_epoch

            if len(epochs) > 1:
                epoch_span = (last_epoch - first_epoch).total_seconds()

                base["epoch_span_ratio"] = min(
                    1.0,
                    max(
                        0.0,
                        epoch_span / requested_seconds,
                    ),
                )

                unique_epochs = epochs.drop_duplicates().sort_values()

                gaps = unique_epochs.diff().dropna().dt.total_seconds() / 3600.0

                if not gaps.empty:
                    base["median_gap_hours"] = float(gaps.median())

                    base["max_gap_hours"] = float(gaps.max())

            if "artifact_id" in frame.columns:
                artifact_ids = tuple(
                    sorted({str(value) for value in frame["artifact_id"].dropna()})
                )

                base["artifact_ids"] = artifact_ids

                base["artifact_count"] = len(artifact_ids)

            numeric = {}

            for field in summary_fields:
                if field not in frame.columns:
                    numeric[field] = None
                    continue

                series = pd.to_numeric(
                    frame[field],
                    errors="coerce",
                )

                numeric[field] = series

                usable = series.dropna()

                if usable.empty:
                    continue

                base[f"{field}_min"] = float(usable.min())

                base[f"{field}_median"] = float(usable.median())

                base[f"{field}_max"] = float(usable.max())

            reasons = []

            if min_coverage is not None and base["observed_day_ratio"] < min_coverage:
                reasons.append("coverage_below_min")

            if active_ranges:
                required_columns = list(active_ranges)

                missing_column = any(
                    numeric.get(field) is None for field in required_columns
                )

                if missing_column:
                    reasons.append("missing_filter_data")

                else:
                    known = pd.Series(
                        True,
                        index=frame.index,
                        dtype=bool,
                    )

                    matches = pd.Series(
                        True,
                        index=frame.index,
                        dtype=bool,
                    )

                    for field, (
                        lower,
                        upper,
                    ) in active_ranges.items():
                        series = numeric[field]

                        known &= series.notna()

                        matches &= series.ge(lower) & series.le(upper)

                    if orbit_match == "all":
                        if not bool(known.all()):
                            reasons.append("missing_filter_data")

                        elif not bool(matches.all()):
                            reasons.append("out_of_range")

                    else:
                        usable_matches = matches[known]

                        if usable_matches.empty:
                            reasons.append("missing_filter_data")

                        elif not bool(usable_matches.any()):
                            reasons.append("out_of_range")

            unique_reasons = []

            for reason in reasons:
                if reason not in unique_reasons:
                    unique_reasons.append(reason)

            base["matches"] = len(unique_reasons) == 0

            base["filter_reason"] = (
                "pass" if base["matches"] else ";".join(unique_reasons)
            )

            output.append(base)

        columns = [
            "norad_id",
            "object_id",
            "cospar_id",
            "name",
            "requested_start",
            "requested_end",
            "orbit_source",
            "orbit_rows",
            "orbit_days",
            "observed_day_ratio",
            "first_epoch",
            "last_epoch",
            "epoch_span_ratio",
            "median_gap_hours",
            "max_gap_hours",
            "artifact_count",
            "artifact_ids",
        ]

        for field in summary_fields:
            columns.extend(
                [
                    f"{field}_min",
                    f"{field}_median",
                    f"{field}_max",
                ]
            )

        columns.extend(
            [
                "matches",
                "filter_reason",
                "error",
            ]
        )

        return pd.DataFrame(
            output,
            columns=columns,
        )

    # ==================================================================
    # Space-Track GP_HISTORY synchronization
    # ==================================================================

    def _sync_gp_history(
        self,
        *,
        source_name: str,
        norad_id: int,
        start: date,
        end: date,
    ) -> None:
        """
        Space-Track GP_HISTORY의 부족한 구간을 다운로드하고
        raw archive + normalization + DuckDB 저장까지 수행한다.
        """

        source = self.get_source(source_name)

        print(f"[{source_name}] downloading NORAD {norad_id}: {start} -> {end}")

        # --------------------------------------------------------------
        # 1. Space-Track raw 다운로드
        # --------------------------------------------------------------

        payload = source.fetch(
            "gp_history",
            norad_id=norad_id,
            start=start,
            end=end,
        )

        # --------------------------------------------------------------
        # 2. raw 원본 보존
        # --------------------------------------------------------------

        artifact = save_raw_artifact(
            source=source_name,
            dataset="gp_history",
            payload=payload,
            norad_id=norad_id,
            start=start,
            end=end,
            metadata={
                "dataset": "gp_history",
                "format": "json",
            },
            extension="json",
        )

        # --------------------------------------------------------------
        # 3. artifact provenance 저장
        # --------------------------------------------------------------

        self._register_artifact(artifact)

        # --------------------------------------------------------------
        # 4. 내부 공통 형식으로 normalization
        # --------------------------------------------------------------

        records = source.normalize(
            "gp_history",
            payload,
        )

        # --------------------------------------------------------------
        # 5. orbit_elements 저장
        # --------------------------------------------------------------

        self.con.execute("BEGIN TRANSACTION")
        try:
            IdentityStore(self.con).ingest(records, artifact, transaction=False)
            self._insert_orbit_records(
                records=records,
                artifact=artifact,
                source_name=source_name,
            )

            # --------------------------------------------------------------
            # 6. coverage 기록
            # --------------------------------------------------------------

            self._register_coverage(
                source_name=source_name,
                dataset="gp_history",
                norad_id=norad_id,
                start=start,
                end=end,
                artifact=artifact,
            )
            self.con.execute("COMMIT")
        except Exception:
            self.con.execute("ROLLBACK")
            raise

        print(f"[Archive] stored {len(records):,} orbit records")

    # ==================================================================
    # Artifact provenance
    # ==================================================================

    def _register_artifact(
        self,
        artifact: RawArtifact,
    ) -> None:
        """
        raw artifact에 대한 provenance 정보를 DuckDB에 저장한다.
        """

        self.con.execute(
            """
            INSERT OR IGNORE INTO artifacts (
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                artifact.artifact_id,
                artifact.source,
                artifact.dataset,
                artifact.norad_id,
                artifact.requested_start,
                artifact.requested_end,
                artifact.retrieved_at,
                artifact.sha256,
                str(artifact.path),
            ],
        )

    # ==================================================================
    # Coverage
    # ==================================================================

    def _register_coverage(
        self,
        *,
        source_name: str,
        dataset: str,
        norad_id: int,
        start: date,
        end: date,
        artifact: RawArtifact,
    ) -> None:
        """
        어떤 source/dataset/object 기간을 확보했는지 기록한다.
        """

        self.con.execute(
            """
            INSERT INTO coverage (
                source,
                dataset,
                norad_id,
                start_date,
                end_date,
                artifact_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                source_name,
                dataset,
                norad_id,
                start,
                end,
                artifact.artifact_id,
            ],
        )

    def coverage(
        self,
        *,
        norad_id: int | None = None,
        source: str | None = None,
        dataset: str | None = None,
    ) -> pd.DataFrame:
        """
        현재 archive에 저장된 coverage를 조회한다.
        """

        query = """
            SELECT *
            FROM coverage
            WHERE 1 = 1
        """

        values: list[Any] = []

        if norad_id is not None:
            query += """
                AND norad_id = ?
            """

            values.append(norad_id)

        if source is not None:
            query += """
                AND source = ?
            """

            values.append(source)

        if dataset is not None:
            query += """
                AND dataset = ?
            """

            values.append(dataset)

        query += """
            ORDER BY
                source,
                dataset,
                norad_id,
                start_date
        """

        return self.con.execute(
            query,
            values,
        ).df()

    # ==================================================================
    # Orbit database insert
    # ==================================================================

    def _insert_orbit_records(
        self,
        *,
        records: list[dict],
        artifact: RawArtifact,
        source_name: str,
    ) -> None:
        """
        normalized orbital elements를 DuckDB에 저장한다.
        """

        if not records:
            return

        rows = []

        for record in records:
            rows.append(
                (
                    record["gp_id"],
                    record["norad_id"],
                    record["object_id"],
                    record["object_name"],
                    record["epoch"],
                    record["mean_motion"],
                    record["eccentricity"],
                    record["inclination_deg"],
                    record["raan_deg"],
                    record["arg_pericenter_deg"],
                    record["mean_anomaly_deg"],
                    record["bstar"],
                    record["semimajor_axis_km"],
                    record["period_min"],
                    record["apoapsis_km"],
                    record["periapsis_km"],
                    record["tle_line1"],
                    record["tle_line2"],
                    source_name,
                    artifact.artifact_id,
                )
            )

        # Repeated identical GP records are idempotent. Conflicting claims
        # must not disappear behind INSERT OR IGNORE; raw artifacts remain.
        claims = {}
        for row in rows:
            previous = claims.get(row[0])
            if previous is not None and previous[:-1] != row[:-1]:
                raise ValueError(f"Conflicting orbital claims for GP ID {row[0]}.")
            claims[row[0]] = row

        existing = self.con.execute(
            "SELECT * FROM orbit_elements WHERE gp_id IN (SELECT unnest(?))",
            [list(claims)],
        ).fetchall()
        for previous in existing:
            if previous[:-1] != claims[previous[0]][:-1]:
                raise ValueError(f"Conflicting orbital claims for GP ID {previous[0]}.")

        self.con.executemany(
            """
            INSERT OR IGNORE INTO orbit_elements (
                gp_id,
                norad_id,
                object_id,
                object_name,
                epoch,
                mean_motion,
                eccentricity,
                inclination_deg,
                raan_deg,
                arg_pericenter_deg,
                mean_anomaly_deg,
                bstar,
                semimajor_axis_km,
                period_min,
                apoapsis_km,
                periapsis_km,
                tle_line1,
                tle_line2,
                source,
                artifact_id
            )
            VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?
            )
            """,
            rows,
        )

    # ==================================================================
    # Archive database information
    # ==================================================================

    def artifacts(
        self,
        *,
        source: str | None = None,
        dataset: str | None = None,
        norad_id: int | None = None,
    ) -> pd.DataFrame:
        """
        저장된 raw artifact 목록과 provenance를 조회한다.
        """

        query = """
            SELECT *
            FROM artifacts
            WHERE 1 = 1
        """

        values: list[Any] = []

        if source is not None:
            query += """
                AND source = ?
            """

            values.append(source)

        if dataset is not None:
            query += """
                AND dataset = ?
            """

            values.append(dataset)

        if norad_id is not None:
            query += """
                AND norad_id = ?
            """

            values.append(norad_id)

        query += """
            ORDER BY retrieved_at DESC
        """

        return self.con.execute(
            query,
            values,
        ).df()

    # ==================================================================
    # Lifecycle
    # ==================================================================

    def msis_inputs(
        self,
        trajectory: pd.DataFrame,
        *,
        driver_source: str,
        trajectory_parents: Iterable[ProductParent],
    ) -> tuple[
        pd.DataFrame,
        tuple[
            ProductParent,
            ...,
        ],
    ]:
        """
        Build explicit NRLMSIS inputs and provenance.

        v0.1.0 supports GFZ as the explicitly selected
        F10.7 / Ap driver source.

        No interpolation, nearest-time matching,
        forward-fill, or implicit source selection occurs.
        """

        if driver_source != "gfz":
            raise ValueError("msis_inputs currently requires driver_source='gfz'.")

        trajectory_parents = tuple(trajectory_parents)

        if not trajectory_parents:
            raise ValueError(
                "trajectory_parents must contain explicit trajectory provenance."
            )

        if not isinstance(
            trajectory,
            pd.DataFrame,
        ):
            raise TypeError("trajectory must be a pandas DataFrame.")

        if trajectory.empty:
            raise ValueError("trajectory must not be empty.")

        if "timestamp" not in (trajectory.columns):
            raise ValueError("trajectory is missing: timestamp")

        timestamps = pd.to_datetime(
            trajectory["timestamp"],
            utc=True,
            errors="raise",
        )

        first_day = timestamps.min().floor("D")

        last_day = timestamps.max().floor("D")

        first_ap_bin = timestamps.min().floor("3h")

        last_ap_bin = timestamps.max().floor("3h")

        f107 = self.timeseries(
            "f107_observed",
            start=(first_day - pd.Timedelta(days=40)),
            end=(last_day + pd.Timedelta(days=41)),
            source=driver_source,
            dataset="f107_observed",
            artifact_resolution="all",
        )

        ap_daily = self.timeseries(
            "ap_daily",
            start=first_day,
            end=(last_day + pd.Timedelta(days=1)),
            source=driver_source,
            dataset="ap_daily",
            artifact_resolution="all",
        )

        ap_3h = self.timeseries(
            "ap",
            start=(first_ap_bin - pd.Timedelta(hours=57)),
            end=(last_ap_bin + pd.Timedelta(hours=3)),
            source=driver_source,
            dataset="ap",
            artifact_resolution="all",
        )

        from orbitoby.models.msis import (
            build_msis_inputs,
        )

        inputs = build_msis_inputs(
            trajectory,
            f107=f107,
            ap_daily=ap_daily,
            ap_3h=ap_3h,
        )

        def raw_parents(
            frame: pd.DataFrame,
            *,
            role: str,
        ) -> tuple[
            ProductParent,
            ...,
        ]:
            if "artifact_id" not in (frame.columns):
                raise ValueError("driver frame has no artifact_id provenance.")

            if frame["artifact_id"].isna().any():
                raise ValueError(
                    "driver frame contains rows without artifact provenance."
                )

            artifact_ids = sorted(
                {str(value) for value in frame["artifact_id"].dropna()}
            )

            if not artifact_ids:
                raise ValueError("driver frame has no raw artifact provenance.")

            return tuple(
                ProductParent(
                    parent_kind=("raw_artifact"),
                    parent_id=(artifact_id),
                    role=role,
                )
                for artifact_id in artifact_ids
            )

        parents = (
            *trajectory_parents,
            *raw_parents(
                f107,
                role=("f107_previous_day_input"),
            ),
            *raw_parents(
                f107,
                role=("f107a_81day_input"),
            ),
            *raw_parents(
                ap_daily,
                role="ap_input",
            ),
            *raw_parents(
                ap_3h,
                role="ap_input",
            ),
        )

        return (
            inputs,
            tuple(parents),
        )

    def msis_density(
        self,
        inputs: pd.DataFrame,
        *,
        parents: Iterable[ProductParent],
        geomagnetic_activity: int = -1,
    ) -> pd.DataFrame:
        """Run NRLMSIS 2.1 and persist explicit model provenance."""

        parents = tuple(parents)

        roles = {parent.role for parent in parents}

        required_roles = {
            "f107_previous_day_input",
            "f107a_81day_input",
            "ap_input",
        }

        missing_roles = required_roles - roles

        if missing_roles:
            raise ValueError(
                "MSIS persistence requires "
                "explicit provenance roles: " + ", ".join(sorted(missing_roles))
            )

        run = calculate_msis_density(
            inputs,
            geomagnetic_activity=(geomagnetic_activity),
        )

        timestamps = pd.to_datetime(
            run.data["timestamp"],
            utc=True,
            errors="raise",
        )

        requested_start = timestamps.min()

        requested_end = timestamps.max() + pd.Timedelta(microseconds=1)

        parameters = {
            "model_name": (run.model_name),
            "model_version": (run.model_version),
            "backend": run.backend,
            "backend_version": (run.backend_version),
            "geomagnetic_activity": (run.geomagnetic_activity),
            "interpolate_indices": (run.interpolate_indices),
            "forcing_policy": ("explicit_only"),
            "f107_previous_day": ("explicit"),
            "f107a_81day_centered": ("explicit"),
            "ap_vector_order": [
                "daily",
                "current_3h",
                "3h_prior",
                "6h_prior",
                "9h_prior",
                "12_33h_avg",
                "36_57h_avg",
            ],
        }

        saved = self.product_store.write(
            run.data,
            dataset=MSIS_DATASET,
            metric=MSIS_METRIC,
            unit=MSIS_UNIT,
            artifact_kind=("model_output"),
            method=MSIS_METHOD,
            model_name=(run.model_name),
            model_version=(run.model_version),
            transform=(MSIS_TRANSFORM),
            transform_version=(MSIS_TRANSFORM_VERSION),
            requested_start=(requested_start),
            requested_end=(requested_end),
            parents=parents,
            parameters=parameters,
        )

        return self.product_store.read_product(saved.product_id)

    def close(self) -> None:
        """
        DuckDB 연결 종료.
        """

        self.con.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()
