from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal

from orbitoby.archive.raw import RawArtifact

QualityStatus = Literal[
    "definitive",
    "provisional",
    "nowcast",
    "predicted",
    "unknown",
]

ArtifactKind = Literal[
    "measurement",
    "provider_derived",
    "modeled",
    "derived",
]

TimestampKind = Literal[
    "field",
    "ymd",
    "ym",
]

StatusScheme = Literal[
    "static",
    "gfz",
    "silso",
    "kyoto",
]

IntervalKind = Literal[
    "instant",
    "minute",
    "30m",
    "hour",
    "3h",
    "day",
    "month",
]


@dataclass(frozen=True, slots=True)
class MetricBinding:
    metric: str
    source: str
    dataset: str
    source_field: str
    unit: str | None

    time_field: str | None = None
    timestamp_kind: TimestampKind = "field"

    status: QualityStatus = "unknown"
    status_field: str | None = None
    status_scheme: StatusScheme = "static"

    artifact_kind: ArtifactKind = "measurement"
    method: str | None = None

    quality_field: str | None = None
    context_fields: tuple[str, ...] = ()

    fill_values: tuple[int | float, ...] = ()

    scale: float = 1.0
    offset: float = 0.0

    interval_kind: IntervalKind = "instant"

    fetch_window: bool = True

    mergeable: bool = False
    priority: int = 0


@dataclass(frozen=True, slots=True)
class CanonicalObservation:
    timestamp: datetime

    metric: str
    value: int | float | None
    unit: str | None

    # Exact provider-normalized value before canonical transforms.
    source_value: Any

    is_missing: bool
    missing_reason: str | None

    source: str
    dataset: str
    source_field: str
    source_version: str | None

    status: QualityStatus
    provider_status: Any
    quality_flag: Any

    artifact_kind: ArtifactKind
    method: str | None

    interval_start: datetime | None
    interval_end: datetime | None

    artifact_id: str | None
    retrieved_at: datetime | None

    transform: str
    transform_version: str

    context: dict[str, Any]

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


def _utc_datetime(
    value: str | date | datetime,
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
            raise ValueError("Canonical timestamp must not be empty.")

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        try:
            result = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError("Canonical timestamp is not valid ISO-8601.") from exc

    else:
        raise TypeError("Canonical timestamp must be str, date, or datetime.")

    if result.tzinfo is None:
        return result.replace(tzinfo=UTC)

    return result.astimezone(UTC)


def _timestamp(
    record: dict,
    binding: MetricBinding,
) -> datetime:
    if binding.timestamp_kind == "field":
        if binding.time_field is None:
            raise RuntimeError("Field timestamp binding has no time_field.")

        if binding.time_field not in record:
            raise KeyError(
                f"{binding.source}/{binding.dataset} "
                f"has no timestamp field "
                f"{binding.time_field!r}."
            )

        return _utc_datetime(record[binding.time_field])

    if binding.timestamp_kind == "ymd":
        return datetime(
            int(record["year"]),
            int(record["month"]),
            int(record["day"]),
            tzinfo=UTC,
        )

    if binding.timestamp_kind == "ym":
        return datetime(
            int(record["year"]),
            int(record["month"]),
            1,
            tzinfo=UTC,
        )

    raise RuntimeError(f"Unsupported timestamp kind: {binding.timestamp_kind!r}")


def _canonical_status(
    record: dict,
    binding: MetricBinding,
) -> tuple[
    QualityStatus,
    Any,
]:
    provider_status = record.get(binding.status_field) if binding.status_field else None

    if binding.status_scheme == "static":
        return (
            binding.status,
            provider_status,
        )

    if provider_status is None:
        return (
            "unknown",
            None,
        )

    if binding.status_scheme == "gfz":
        text = str(provider_status).strip().lower()

        mapping: dict[str, QualityStatus] = {
            "def": "definitive",
            "definitive": "definitive",
            "nowcast": "nowcast",
            "provisional": "provisional",
            "prov": "provisional",
        }

        return (
            mapping.get(
                text,
                "unknown",
            ),
            provider_status,
        )

    if binding.status_scheme == "silso":
        try:
            value = int(provider_status)
        except (TypeError, ValueError):
            return (
                "unknown",
                provider_status,
            )

        if value == 1:
            return (
                "definitive",
                provider_status,
            )

        if value == 0:
            return (
                "provisional",
                provider_status,
            )

        return (
            "unknown",
            provider_status,
        )

    if binding.status_scheme == "kyoto":
        try:
            version = int(provider_status)
        except (TypeError, ValueError):
            return (
                "unknown",
                provider_status,
            )

        major = version // 10

        if major == 0:
            status: QualityStatus = "nowcast"
        elif major == 1:
            status = "provisional"
        elif major == 2:
            status = "definitive"
        else:
            status = "unknown"

        return (
            status,
            provider_status,
        )

    raise RuntimeError(f"Unsupported status scheme: {binding.status_scheme!r}")


def _value(
    source_value: Any,
    binding: MetricBinding,
) -> tuple[
    int | float | None,
    bool,
    str | None,
]:
    if source_value is None:
        return (
            None,
            True,
            "provider_null",
        )

    if isinstance(
        source_value,
        bool,
    ):
        raise TypeError(
            f"Canonical metric {binding.metric!r} received a boolean value."
        )

    if source_value in binding.fill_values:
        return (
            None,
            True,
            "provider_fill",
        )

    if not isinstance(
        source_value,
        (
            int,
            float,
        ),
    ):
        raise TypeError(
            f"Canonical metric "
            f"{binding.metric!r} received "
            f"non-numeric provider value "
            f"{type(source_value).__name__!r}."
        )

    value = source_value * binding.scale + binding.offset

    return (
        value,
        False,
        None,
    )


def _interval(
    timestamp: datetime,
    kind: IntervalKind,
) -> tuple[
    datetime | None,
    datetime | None,
]:
    if kind == "instant":
        return (
            None,
            None,
        )

    if kind == "minute":
        delta = timedelta(minutes=1)

    elif kind == "30m":
        delta = timedelta(minutes=30)

    elif kind == "hour":
        delta = timedelta(hours=1)

    elif kind == "3h":
        delta = timedelta(hours=3)

    elif kind == "day":
        delta = timedelta(days=1)

    elif kind == "month":
        if timestamp.month == 12:
            end = datetime(
                timestamp.year + 1,
                1,
                1,
                tzinfo=UTC,
            )
        else:
            end = datetime(
                timestamp.year,
                timestamp.month + 1,
                1,
                tzinfo=UTC,
            )

        return (
            timestamp,
            end,
        )

    else:
        raise RuntimeError(f"Unsupported interval kind: {kind!r}")

    return (
        timestamp,
        timestamp + delta,
    )


def canonicalize_records(
    records: list[dict],
    binding: MetricBinding,
    *,
    artifact: RawArtifact | None,
) -> list[dict[str, Any]]:
    """Create provenance-rich canonical scientific records.

    Provider-native normalized values remain available through
    ``source_value``. Documented fill values become explicit
    canonical missing values; they are never interpreted as
    physical measurements.

    No interpolation, smoothing, averaging or forward-fill occurs.
    """

    output: list[dict[str, Any]] = []

    for row_index, record in enumerate(records):
        if binding.source_field not in record:
            raise KeyError(
                f"{binding.source}/"
                f"{binding.dataset} row "
                f"{row_index} has no mapped "
                f"field "
                f"{binding.source_field!r}."
            )

        timestamp = _timestamp(
            record,
            binding,
        )

        source_value = record[binding.source_field]

        (
            value,
            is_missing,
            missing_reason,
        ) = _value(
            source_value,
            binding,
        )

        (
            status,
            provider_status,
        ) = _canonical_status(
            record,
            binding,
        )

        (
            interval_start,
            interval_end,
        ) = _interval(
            timestamp,
            binding.interval_kind,
        )

        context = {key: record[key] for key in binding.context_fields if key in record}

        observation = CanonicalObservation(
            timestamp=timestamp,
            metric=binding.metric,
            value=value,
            unit=binding.unit,
            source_value=(source_value),
            is_missing=(is_missing),
            missing_reason=(missing_reason),
            source=(binding.source),
            dataset=(binding.dataset),
            source_field=(binding.source_field),
            source_version=None,
            status=status,
            provider_status=(provider_status),
            quality_flag=(
                record.get(binding.quality_field) if binding.quality_field else None
            ),
            artifact_kind=(binding.artifact_kind),
            method=binding.method,
            interval_start=(interval_start),
            interval_end=(interval_end),
            artifact_id=(artifact.artifact_id if artifact is not None else None),
            retrieved_at=(artifact.retrieved_at if artifact is not None else None),
            transform=("orbitoby.canonical"),
            transform_version="1",
            context=context,
        ).as_record()

        observation["_binding_priority"] = binding.priority

        output.append(observation)

    return output


# ======================================================================
# NRCan
# ======================================================================

_NRCAN_DATASETS = (
    (
        "f107_measurements",
        0,
        "instant",
    ),
    (
        "f107_legacy_measurements_1996_2007",
        10,
        "instant",
    ),
    (
        "f107_legacy_daily_1947_1996",
        20,
        "day",
    ),
)

_NRCAN_BINDINGS = tuple(
    MetricBinding(
        metric=metric,
        source="nrcan",
        dataset=dataset,
        source_field=metric,
        time_field="time",
        unit="sfu",
        interval_kind=interval_kind,
        mergeable=True,
        priority=priority,
    )
    for dataset, priority, interval_kind in _NRCAN_DATASETS
    for metric in (
        "f107_observed",
        "f107_adjusted",
        "f107_series_d",
    )
)


# ======================================================================
# GFZ
# ======================================================================

_GFZ_SPECS = (
    (
        "kp",
        "kp",
        "Kp",
        "1",
        "3h",
    ),
    (
        "ap",
        "ap",
        "ap",
        "2 nT",
        "3h",
    ),
    (
        "ap_daily",
        "ap_daily",
        "Ap",
        "2 nT",
        "day",
    ),
    (
        "cp",
        "cp",
        "Cp",
        "1",
        "day",
    ),
    (
        "c9",
        "c9",
        "C9",
        "1",
        "day",
    ),
    (
        "hp30",
        "hp30",
        "Hp30",
        "1",
        "30m",
    ),
    (
        "hp60",
        "hp60",
        "Hp60",
        "1",
        "hour",
    ),
    (
        "ap30",
        "ap30",
        "ap30",
        "2 nT",
        "30m",
    ),
    (
        "ap60",
        "ap60",
        "ap60",
        "2 nT",
        "hour",
    ),
    (
        "ssn",
        "sunspot",
        "SN",
        "1",
        "day",
    ),
    (
        "f107_observed",
        "f107_observed",
        "Fobs",
        "sfu",
        "day",
    ),
    (
        "f107_adjusted",
        "f107_adjusted",
        "Fadj",
        "sfu",
        "day",
    ),
)

_GFZ_BINDINGS = tuple(
    MetricBinding(
        metric=metric,
        source="gfz",
        dataset=dataset,
        source_field=field,
        time_field="datetime",
        unit=unit,
        status_field="status",
        status_scheme="gfz",
        interval_kind=interval,
    )
    for (
        metric,
        dataset,
        field,
        unit,
        interval,
    ) in _GFZ_SPECS
)


# ======================================================================
# SILSO
# ======================================================================

_SILSO_COMMON = {
    "source": "silso",
    "source_field": "sunspot_number",
    "unit": "1",
    "status_field": "definitive",
    "status_scheme": "silso",
    "fill_values": (-1,),
    "context_fields": (
        "decimal_year",
        "standard_deviation",
        "observations",
    ),
}

_SILSO_BINDINGS = (
    MetricBinding(
        metric="ssn",
        dataset="sunspot_daily",
        timestamp_kind="ymd",
        interval_kind="day",
        **_SILSO_COMMON,
    ),
    MetricBinding(
        metric="ssn_monthly",
        dataset="sunspot_monthly",
        timestamp_kind="ym",
        interval_kind="month",
        **_SILSO_COMMON,
    ),
    MetricBinding(
        metric="ssn_monthly_smoothed",
        dataset=("sunspot_monthly_smoothed"),
        timestamp_kind="ym",
        interval_kind="month",
        **_SILSO_COMMON,
    ),
)


# ======================================================================
# NOAA real-time solar wind
# ======================================================================

_NOAA_BINDINGS = (
    MetricBinding(
        metric="solar_wind_speed",
        source="noaa",
        dataset="rtsw_wind_1m",
        source_field="proton_speed",
        time_field="time_tag",
        unit="km/s",
        fetch_window=False,
        context_fields=(
            "active",
            "source",
        ),
    ),
    MetricBinding(
        metric=("solar_wind_proton_temperature"),
        source="noaa",
        dataset="rtsw_wind_1m",
        source_field=("proton_temperature"),
        time_field="time_tag",
        unit="K",
        fetch_window=False,
        context_fields=(
            "active",
            "source",
        ),
    ),
    MetricBinding(
        metric=("solar_wind_proton_density"),
        source="noaa",
        dataset="rtsw_wind_1m",
        source_field=("proton_density"),
        time_field="time_tag",
        unit="1/cm^3",
        fetch_window=False,
        context_fields=(
            "active",
            "source",
        ),
    ),
    MetricBinding(
        metric="imf_bt",
        source="noaa",
        dataset="rtsw_mag_1m",
        source_field="bt",
        time_field="time_tag",
        unit="nT",
        fetch_window=False,
        context_fields=(
            "active",
            "source",
        ),
    ),
    MetricBinding(
        metric="imf_bx_gse",
        source="noaa",
        dataset="rtsw_mag_1m",
        source_field="bx_gse",
        time_field="time_tag",
        unit="nT",
        fetch_window=False,
        context_fields=(
            "active",
            "source",
        ),
    ),
    MetricBinding(
        metric="imf_by_gse",
        source="noaa",
        dataset="rtsw_mag_1m",
        source_field="by_gse",
        time_field="time_tag",
        unit="nT",
        fetch_window=False,
        context_fields=(
            "active",
            "source",
        ),
    ),
    MetricBinding(
        metric="imf_bz_gse",
        source="noaa",
        dataset="rtsw_mag_1m",
        source_field="bz_gse",
        time_field="time_tag",
        unit="nT",
        fetch_window=False,
        context_fields=(
            "active",
            "source",
        ),
    ),
)


# ======================================================================
# WDC Kyoto
# ======================================================================

_KYOTO_STATUS = {
    "source": "wdc_kyoto",
    "time_field": "Time",
    "status_field": "versionCode",
    "status_scheme": "kyoto",
}

_KYOTO_BINDINGS = (
    MetricBinding(
        metric="dst",
        dataset="dst_hourly",
        source_field="dstValue",
        unit="nT",
        fill_values=(99999,),
        **_KYOTO_STATUS,
    ),
    *tuple(
        MetricBinding(
            metric=metric,
            dataset=dataset,
            source_field=field,
            unit="nT",
            fill_values=(99999,),
            **_KYOTO_STATUS,
        )
        for dataset in (
            "ae_hourly",
            "ae_minute",
        )
        for metric, field in (
            (
                "ae",
                "aeValue",
            ),
            (
                "al",
                "alValue",
            ),
            (
                "au",
                "auValue",
            ),
            (
                "ao",
                "aoValue",
            ),
        )
    ),
    *tuple(
        MetricBinding(
            metric=metric,
            dataset="asysym_minute",
            source_field=field,
            unit="nT",
            fill_values=(99999,),
            **_KYOTO_STATUS,
        )
        for metric, field in (
            (
                "asy_d",
                "asyDValue",
            ),
            (
                "asy_h",
                "asyHValue",
            ),
            (
                "sym_d",
                "symDValue",
            ),
            (
                "sym_h",
                "symHValue",
            ),
        )
    ),
    MetricBinding(
        metric="kp",
        dataset="kp_ap_3hour",
        source_field="kpValue",
        unit="1",
        fill_values=(99.9,),
        **_KYOTO_STATUS,
    ),
    MetricBinding(
        metric="ap",
        dataset="kp_ap_3hour",
        source_field="apValue",
        unit="2 nT",
        fill_values=(999,),
        **_KYOTO_STATUS,
    ),
    MetricBinding(
        metric="ap_daily",
        dataset="ap_daily",
        source_field="apValue",
        unit="2 nT",
        fill_values=(999,),
        **_KYOTO_STATUS,
    ),
)


# ======================================================================
# CDAWeb / OMNI hourly
# ======================================================================

_CDAWEB_BINDINGS = (
    MetricBinding(
        metric="imf_bt",
        source="cdaweb",
        dataset="omni_hourly",
        source_field="ABS_B1800",
        time_field="Time",
        unit="nT",
        fill_values=(999.9,),
    ),
    MetricBinding(
        metric="imf_bx_gse",
        source="cdaweb",
        dataset="omni_hourly",
        source_field="BX_GSE1800",
        time_field="Time",
        unit="nT",
        fill_values=(999.9,),
    ),
    MetricBinding(
        metric="imf_by_gse",
        source="cdaweb",
        dataset="omni_hourly",
        source_field="BY_GSE1800",
        time_field="Time",
        unit="nT",
        fill_values=(999.9,),
    ),
    MetricBinding(
        metric="imf_bz_gse",
        source="cdaweb",
        dataset="omni_hourly",
        source_field="BZ_GSE1800",
        time_field="Time",
        unit="nT",
        fill_values=(999.9,),
    ),
    MetricBinding(
        metric="imf_by_gsm",
        source="cdaweb",
        dataset="omni_hourly",
        source_field="BY_GSM1800",
        time_field="Time",
        unit="nT",
        fill_values=(999.9,),
    ),
    MetricBinding(
        metric="imf_bz_gsm",
        source="cdaweb",
        dataset="omni_hourly",
        source_field="BZ_GSM1800",
        time_field="Time",
        unit="nT",
        fill_values=(999.9,),
    ),
    MetricBinding(
        metric="solar_wind_speed",
        source="cdaweb",
        dataset="omni_hourly",
        source_field="V1800",
        time_field="Time",
        unit="km/s",
        fill_values=(9999.0,),
    ),
    MetricBinding(
        metric=("solar_wind_proton_density"),
        source="cdaweb",
        dataset="omni_hourly",
        source_field="N1800",
        time_field="Time",
        unit="1/cm^3",
        fill_values=(999.9,),
    ),
    MetricBinding(
        metric=("solar_wind_proton_temperature"),
        source="cdaweb",
        dataset="omni_hourly",
        source_field="T1800",
        time_field="Time",
        unit="K",
        fill_values=(9999999.0,),
    ),
)


# ======================================================================
# Swarm
# ======================================================================

_SWARM_CONTEXT = (
    "Latitude_GD",
    "Longitude_GD",
    "Height_GD",
    "local_solar_time",
)

_SWARM_ACC_DATASETS = (
    "density_a_acc",
    "density_b_acc",
    "density_c_acc",
)

_SWARM_POD_DATASETS = (
    "density_a_pod",
    "density_b_pod",
    "density_c_pod",
)

_SWARM_BINDINGS = (
    *tuple(
        MetricBinding(
            metric=("thermosphere_neutral_mass_density"),
            source="swarm",
            dataset=dataset,
            source_field="density",
            time_field="Timestamp",
            unit="kg/m^3",
            fill_values=(9.99e32,),
            artifact_kind=("provider_derived"),
            method="accelerometer_retrieval",
            context_fields=(_SWARM_CONTEXT),
        )
        for dataset in _SWARM_ACC_DATASETS
    ),
    *tuple(
        MetricBinding(
            metric=("thermosphere_neutral_mass_density"),
            source="swarm",
            dataset=dataset,
            source_field="density",
            time_field="Timestamp",
            unit="kg/m^3",
            fill_values=(9.99e32,),
            artifact_kind=("provider_derived"),
            method="pod_retrieval",
            quality_field=("validity_flag"),
            context_fields=(_SWARM_CONTEXT),
        )
        for dataset in _SWARM_POD_DATASETS
    ),
    *tuple(
        MetricBinding(
            metric=("thermosphere_neutral_mass_density_orbit_mean"),
            source="swarm",
            dataset=dataset,
            source_field=("density_orbitmean"),
            time_field="Timestamp",
            unit="kg/m^3",
            artifact_kind=("provider_derived"),
            method="pod_retrieval",
            quality_field=("validity_flag"),
            context_fields=(_SWARM_CONTEXT),
        )
        for dataset in _SWARM_POD_DATASETS
    ),
)


METRIC_BINDINGS: tuple[
    MetricBinding,
    ...,
] = (
    *_NRCAN_BINDINGS,
    *_GFZ_BINDINGS,
    *_SILSO_BINDINGS,
    *_NOAA_BINDINGS,
    *_KYOTO_BINDINGS,
    *_CDAWEB_BINDINGS,
    *_SWARM_BINDINGS,
)


def adapter_metric_bindings(
    adapter,
) -> tuple[
    MetricBinding,
    ...,
]:
    """Return and validate canonical bindings declared by one adapter."""

    bindings = tuple(
        getattr(
            adapter,
            "canonical_bindings",
            (),
        )
    )

    seen: set[
        tuple[
            str,
            str,
            str,
            str,
        ]
    ] = set()

    for binding in bindings:
        if not isinstance(
            binding,
            MetricBinding,
        ):
            raise TypeError(
                f"Source {adapter.name!r} canonical_bindings "
                "must contain MetricBinding instances."
            )

        if binding.source != adapter.name:
            raise ValueError(
                f"Canonical binding source {binding.source!r} "
                f"does not match adapter name {adapter.name!r}."
            )

        if binding.dataset not in adapter.datasets:
            raise ValueError(
                f"Canonical binding dataset {binding.dataset!r} "
                f"is not exposed by source {adapter.name!r}."
            )

        key = (
            binding.metric,
            binding.source,
            binding.dataset,
            binding.source_field,
        )

        if key in seen:
            raise ValueError(
                "Duplicate canonical binding declared by "
                f"source {adapter.name!r}: {key!r}"
            )

        seen.add(key)

    return bindings


def bindings_for_metric(
    metric: str,
) -> tuple[
    MetricBinding,
    ...,
]:
    return tuple(binding for binding in METRIC_BINDINGS if binding.metric == metric)


def canonical_metrics() -> tuple[
    str,
    ...,
]:
    return tuple(sorted({binding.metric for binding in METRIC_BINDINGS}))
