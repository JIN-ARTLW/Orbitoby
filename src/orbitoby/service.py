from __future__ import annotations

from datetime import date
from typing import Any, Self

import pandas as pd

from orbitoby.archive.raw import (
    RawArtifact,
    save_raw_artifact,
)
from orbitoby.catalogue import CatalogueAPI
from orbitoby.source_api import SourceAPI
from orbitoby.sources.base import SourceAdapter
from orbitoby.sources.registry import build_sources
from orbitoby.warehouse.coverage import missing_ranges
from orbitoby.warehouse.db import connect_db
from orbitoby.warehouse.identity import IdentityStore


class Archive(CatalogueAPI, SourceAPI):
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

    def __init__(self) -> None:
        self.con = connect_db()

        # registry에 등록된 모든 source adapter를 로드한다.
        self.sources: dict[str, SourceAdapter] = build_sources()

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

    def fetch(
        self,
        *,
        source: str,
        dataset: str,
        archive_raw: bool = True,
        **params: Any,
    ) -> pd.DataFrame:
        """
        임의의 source/dataset을 조회한다.

        예:
            archive.fetch(
                source="celestrak",
                dataset="satcat",
                norad_id=25544,
            )

            archive.fetch(
                source="noaa",
                dataset="solar_cycle",
            )

        Parameters
        ----------
        source:
            데이터 출처 이름.

        dataset:
            해당 source에서 제공하는 dataset 이름.

        archive_raw:
            True이면 원본 응답을 raw archive에 보존한다.

        **params:
            source별 query parameter.
        """

        for key in ("start", "end"):
            if params.get(key) is not None:
                params[key] = self._parse_date(params[key])
        adapter = self.get_source(source)

        # --------------------------------------------------------------
        # 1. 외부 source에서 raw 데이터 다운로드
        # --------------------------------------------------------------

        payload = adapter.fetch(
            dataset,
            **params,
        )

        # --------------------------------------------------------------
        # 2. 원본 raw archive
        # --------------------------------------------------------------

        if archive_raw:
            extension = "tsv" if source == "gcat" else "json"

            artifact = save_raw_artifact(
                source=source,
                dataset=dataset,
                payload=payload,
                norad_id=params.get("norad_id"),
                start=params.get("start"),
                end=params.get("end"),
                metadata={"params": {key: str(value) for key, value in params.items()}},
                extension=extension,
            )

            self._register_artifact(artifact)

        # --------------------------------------------------------------
        # 3. source-specific response → Python records
        # --------------------------------------------------------------

        records = adapter.normalize(
            dataset,
            payload,
            **params,
        )

        # --------------------------------------------------------------
        # 4. DataFrame 반환
        # --------------------------------------------------------------

        if archive_raw:
            # Index the full response; SatNOGS local limits only affect display.
            index_params = {
                k: v for k, v in params.items() if k not in {"limit", "local_limit"}
            }
            indexed_records = adapter.normalize(dataset, payload, **index_params)
            IdentityStore(self.con).ingest(indexed_records, artifact)

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

        if start_date > end_date:
            raise ValueError("start must be <= end")

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
                end=end_date,
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
              AND CAST(epoch AS DATE)
                    BETWEEN ? AND ?
            ORDER BY epoch
            """,
            [
                norad_id,
                source,
                start_date,
                end_date,
            ],
        ).df()

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
