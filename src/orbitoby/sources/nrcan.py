from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, ClassVar, Literal

from orbitoby.http import SafeHttpClient
from orbitoby.sources.base import SourceAdapter
from orbitoby.sources.metadata import source_metadata


@dataclass(frozen=True, slots=True)
class NRCanArtifactSpec:
    """Provider-native NRCan F10.7 artifact contract."""

    url: str
    format: Literal[
        "current",
        "legacy_daily",
        "legacy_measurements",
    ]


NRCAN_ARTIFACTS: dict[str, NRCanArtifactSpec] = {
    "f107_measurements": NRCanArtifactSpec(
        url=(
            "https://spaceweather.gc.ca/solar_flux_data/daily_flux_values/fluxtable.txt"
        ),
        format="current",
    ),
    "f107_legacy_daily_1947_1996": NRCanArtifactSpec(
        url=(
            "https://spaceweather.gc.ca/"
            "solar_flux_data/daily_flux_values/"
            "F107_1947_1996.txt"
        ),
        format="legacy_daily",
    ),
    "f107_legacy_measurements_1996_2007": NRCanArtifactSpec(
        url=(
            "https://spaceweather.gc.ca/"
            "solar_flux_data/daily_flux_values/"
            "F107_1996_2007.txt"
        ),
        format="legacy_measurements",
    ),
}


class NRCanSource(SourceAdapter):
    """Canadian 10.7 cm solar radio flux measurements."""

    name = "nrcan"
    datasets = tuple(NRCAN_ARTIFACTS)
    raw_extension = "txt"

    ARTIFACTS: ClassVar[dict[str, NRCanArtifactSpec]] = NRCAN_ARTIFACTS

    def __init__(
        self,
        *,
        http: SafeHttpClient | None = None,
    ) -> None:
        self.metadata = source_metadata(self.name)

        self.http = http or SafeHttpClient(
            allowed_hosts=self.metadata.host_allowlist,
            read_timeout=120.0,
            max_bytes=16 * 1024 * 1024,
        )

    @staticmethod
    def _datetime_utc(
        value: str | date | datetime,
        *,
        name: str,
    ) -> datetime:
        if isinstance(value, datetime):
            result = value

        elif isinstance(value, date):
            result = datetime(
                value.year,
                value.month,
                value.day,
                tzinfo=UTC,
            )

        elif isinstance(value, str):
            text = value.strip()

            if not text:
                raise ValueError(f"{name} must not be empty")

            if text.endswith("Z"):
                text = text[:-1] + "+00:00"

            try:
                result = datetime.fromisoformat(text)
            except ValueError as exc:
                raise ValueError(f"{name} is not a valid ISO-8601 date/time") from exc

        else:
            raise TypeError(f"{name} must be str, date, or datetime")

        if result.tzinfo is None:
            result = result.replace(tzinfo=UTC)
        else:
            result = result.astimezone(UTC)

        return result

    @staticmethod
    def _iso_z(value: datetime) -> str:
        return (
            value.astimezone(UTC)
            .isoformat()
            .replace(
                "+00:00",
                "Z",
            )
        )

    @staticmethod
    def _measurement_time(
        fluxdate: str,
        fluxtime: str,
    ) -> datetime:
        fluxdate = fluxdate.strip()
        fluxtime = fluxtime.strip()

        if len(fluxdate) != 8:
            raise ValueError("Invalid NRCan flux date.")

        if len(fluxtime) != 6:
            raise ValueError("Invalid NRCan flux time.")

        try:
            return datetime(
                int(fluxdate[0:4]),
                int(fluxdate[4:6]),
                int(fluxdate[6:8]),
                int(fluxtime[0:2]),
                int(fluxtime[2:4]),
                int(fluxtime[4:6]),
                tzinfo=UTC,
            )
        except ValueError as exc:
            raise ValueError("Invalid NRCan measurement date/time.") from exc

    @staticmethod
    def _historical_measurement_time(
        year: str,
        month: str,
        day: str,
        hhmm: str,
    ) -> datetime:
        hhmm = hhmm.strip()

        if len(hhmm) != 4:
            raise ValueError("Invalid historical NRCan UT field.")

        try:
            return datetime(
                int(year),
                int(month),
                int(day),
                int(hhmm[:2]),
                int(hhmm[2:]),
                tzinfo=UTC,
            )
        except ValueError as exc:
            raise ValueError("Invalid historical NRCan measurement date/time.") from exc

    @staticmethod
    def _julian_datetime(
        julian_day: float,
    ) -> datetime:
        # Julian Date 2440587.5 =
        # 1970-01-01T00:00:00Z.
        seconds = round((julian_day - 2440587.5) * 86400)

        return datetime(
            1970,
            1,
            1,
            tzinfo=UTC,
        ) + timedelta(seconds=seconds)

    @classmethod
    def _context_range(
        cls,
        context: dict[str, Any],
    ) -> tuple[datetime | None, datetime | None]:
        start = context.get("start")
        end = context.get("end")

        start_dt = (
            cls._datetime_utc(
                start,
                name="start",
            )
            if start is not None
            else None
        )

        end_dt = (
            cls._datetime_utc(
                end,
                name="end",
            )
            if end is not None
            else None
        )

        if start_dt is not None and end_dt is not None and start_dt >= end_dt:
            raise ValueError("start must be before end.")

        return start_dt, end_dt

    @staticmethod
    def _inside_range(
        timestamp: datetime,
        start: datetime | None,
        end: datetime | None,
    ) -> bool:
        if start is not None and timestamp < start:
            return False

        return not (end is not None and timestamp >= end)

    @classmethod
    def _record(
        cls,
        *,
        timestamp: datetime,
        julian_day: str,
        carrington: str,
        observed: str,
        adjusted: str,
        series_d: str,
        provider_extra_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        record: dict[str, Any] = {
            "time": cls._iso_z(timestamp),
            "julian_day": float(julian_day),
            "carrington_rotation": float(carrington),
            "f107_observed": float(observed),
            "f107_adjusted": float(adjusted),
            "f107_series_d": float(series_d),
            "unit": "sfu",
        }

        if provider_extra_fields:
            # These fields occur in later rows of the
            # legacy 1996-2007 artifact. Their semantics
            # are not inferred by Orbitoby.
            record["provider_extra_fields"] = list(provider_extra_fields)

        return record

    def fetch(
        self,
        dataset: str,
        **params: Any,
    ) -> bytes:
        try:
            artifact = self.ARTIFACTS[dataset]
        except KeyError as exc:
            raise ValueError(f"Unsupported NRCan dataset: {dataset!r}") from exc

        allowed = {
            "start",
            "end",
        }

        unknown = set(params) - allowed

        if unknown:
            raise ValueError(
                "Unsupported NRCan fetch parameter(s): " + ", ".join(sorted(unknown))
            )

        start = params.get("start")
        end = params.get("end")

        if (
            start is not None
            and end is not None
            and self._datetime_utc(
                start,
                name="start",
            )
            >= self._datetime_utc(
                end,
                name="end",
            )
        ):
            raise ValueError("start must be before end.")

        # Provider artifacts are static text tables.
        # Preserve each artifact independently and
        # perform range filtering during normalization.
        return self.http.get(artifact.url)

    def normalize(
        self,
        dataset: str,
        payload: bytes,
        **context: Any,
    ) -> list[dict]:
        try:
            artifact = self.ARTIFACTS[dataset]
        except KeyError as exc:
            raise ValueError(f"Unsupported NRCan dataset: {dataset!r}") from exc

        try:
            text = payload.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise RuntimeError("NRCan F10.7 archive is not valid UTF-8.") from exc

        start_dt, end_dt = self._context_range(context)

        if artifact.format == "current":
            return self._normalize_current(
                text,
                start=start_dt,
                end=end_dt,
            )

        if artifact.format == "legacy_daily":
            return self._normalize_legacy_daily(
                text,
                start=start_dt,
                end=end_dt,
            )

        if artifact.format == "legacy_measurements":
            return self._normalize_legacy_measurements(
                text,
                start=start_dt,
                end=end_dt,
            )

        raise RuntimeError("Unknown NRCan artifact format.")

    def _normalize_current(
        self,
        text: str,
        *,
        start: datetime | None,
        end: datetime | None,
    ) -> list[dict]:
        records = []

        for line_number, line in enumerate(
            text.splitlines(),
            start=1,
        ):
            line = line.strip()

            if not line:
                continue

            if line.startswith("fluxdate"):
                continue

            if line.startswith("----------"):
                continue

            fields = line.split()

            if len(fields) != 7:
                raise ValueError(
                    f"Unexpected NRCan current F10.7 record at line {line_number}."
                )

            (
                fluxdate,
                fluxtime,
                julian_day,
                carrington,
                observed,
                adjusted,
                series_d,
            ) = fields

            timestamp = self._measurement_time(
                fluxdate,
                fluxtime,
            )

            if not self._inside_range(
                timestamp,
                start,
                end,
            ):
                continue

            records.append(
                self._record(
                    timestamp=timestamp,
                    julian_day=julian_day,
                    carrington=carrington,
                    observed=observed,
                    adjusted=adjusted,
                    series_d=series_d,
                )
            )

        return records

    def _normalize_legacy_daily(
        self,
        text: str,
        *,
        start: datetime | None,
        end: datetime | None,
    ) -> list[dict]:
        records = []

        for line_number, line in enumerate(
            text.splitlines(),
            start=1,
        ):
            line = line.strip()

            if not line:
                continue

            if line.startswith('"'):
                continue

            fields = [item.strip() for item in line.split(",")]

            parse_recovery = None

            if len(fields) != 8:
                # The official provider artifact has
                # at least one malformed historical
                # record where a comma delimiter is
                # missing between the last two flux
                # values.
                #
                # Recovery is deliberately narrow:
                # the entire row must still resolve to
                # exactly eight numeric provider fields.
                fallback = re.findall(
                    (
                        r"[+-]?(?:"
                        r"\d+(?:\.\d*)?"
                        r"|\.\d+"
                        r")"
                    ),
                    line,
                )

                if len(fallback) != 8:
                    raise ValueError(
                        f"Unexpected NRCan legacy-daily record at line {line_number}."
                    )

                fields = fallback
                parse_recovery = "missing_comma_recovered"

            (
                julian_day,
                carrington,
                year,
                month,
                day,
                observed,
                adjusted,
                series_d,
            ) = fields

            try:
                provider_date = date(
                    int(year),
                    int(month),
                    int(day),
                )
            except ValueError as exc:
                raise ValueError(
                    f"Invalid NRCan legacy-daily date at line {line_number}."
                ) from exc

            timestamp = self._julian_datetime(float(julian_day))

            if timestamp.date() != provider_date:
                raise ValueError(
                    f"NRCan legacy Julian/date mismatch at line {line_number}."
                )

            if not self._inside_range(
                timestamp,
                start,
                end,
            ):
                continue

            record = self._record(
                timestamp=timestamp,
                julian_day=julian_day,
                carrington=carrington,
                observed=observed,
                adjusted=adjusted,
                series_d=series_d,
            )

            if parse_recovery is not None:
                record["provider_parse_recovery"] = parse_recovery

            records.append(record)

        return records

    def _normalize_legacy_measurements(
        self,
        text: str,
        *,
        start: datetime | None,
        end: datetime | None,
    ) -> list[dict]:
        records = []

        for line_number, line in enumerate(
            text.splitlines(),
            start=1,
        ):
            line = line.strip()

            if not line:
                continue

            if line.startswith("Julian Day"):
                continue

            if line.startswith("Number"):
                continue

            if line.startswith("="):
                continue

            fields = line.split()

            # Provider records can retain a valid
            # observation timestamp while all three
            # flux values are absent.
            #
            # Preserve such rows explicitly rather
            # than treating missing values as zero or
            # silently dropping the provider record.
            if len(fields) == 6:
                (
                    julian_day,
                    carrington,
                    year,
                    month,
                    day,
                    hhmm,
                ) = fields

                timestamp = self._historical_measurement_time(
                    year,
                    month,
                    day,
                    hhmm,
                )

                if not self._inside_range(
                    timestamp,
                    start,
                    end,
                ):
                    continue

                records.append(
                    {
                        "time": self._iso_z(timestamp),
                        "julian_day": float(julian_day),
                        "carrington_rotation": float(carrington),
                        "f107_observed": None,
                        "f107_adjusted": None,
                        "f107_series_d": None,
                        "unit": "sfu",
                        "provider_record_status": ("missing_flux_values"),
                    }
                )

                continue

            if len(fields) < 9:
                raise ValueError(
                    f"Unexpected NRCan legacy-measurement record at line {line_number}."
                )

            (
                julian_day,
                carrington,
                year,
                month,
                day,
                hhmm,
                observed,
                adjusted,
                series_d,
                *provider_extra_fields,
            ) = fields

            timestamp = self._historical_measurement_time(
                year,
                month,
                day,
                hhmm,
            )

            if not self._inside_range(
                timestamp,
                start,
                end,
            ):
                continue

            records.append(
                self._record(
                    timestamp=timestamp,
                    julian_day=julian_day,
                    carrington=carrington,
                    observed=observed,
                    adjusted=adjusted,
                    series_d=series_d,
                    provider_extra_fields=(provider_extra_fields),
                )
            )

        return records
