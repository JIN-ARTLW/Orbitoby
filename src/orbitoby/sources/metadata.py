from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

SourceStatus = Literal[
    "stable",
    "experimental",
    "restricted",
    "deprecated",
]

AuthKind = Literal[
    "none",
    "account",
    "api_key",
    "token",
    "custom",
]


@dataclass(frozen=True, slots=True)
class DatasetDescriptor:
    name: str
    categories: tuple[str, ...] = ()
    description_en: str = ""
    description_ko: str = ""
    auth_required: bool = False


@dataclass(frozen=True, slots=True)
class SourcePolicy:
    license_name: str | None = None
    license_url: str | None = None
    terms_url: str | None = None
    citation_required: bool | None = None

    # Unknown is intentional until provider policy is verified.
    commercial_use: Literal[
        "allowed",
        "restricted",
        "unknown",
    ] = "unknown"

    redistribution: Literal[
        "allowed",
        "restricted",
        "unknown",
    ] = "unknown"


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    name: str
    title: str
    homepage: str
    docs_url: str | None = None
    auth: AuthKind = "none"
    status: SourceStatus = "experimental"

    categories: tuple[str, ...] = ()
    host_allowlist: tuple[str, ...] = ()

    description_en: str = ""
    description_ko: str = ""

    datasets: tuple[DatasetDescriptor, ...] = ()
    policy: SourcePolicy = field(default_factory=SourcePolicy)


def builtin_source_metadata() -> dict[str, SourceMetadata]:
    """Metadata for Orbitoby's built-in providers.

    Legal/policy fields stay explicitly unknown until individually
    verified rather than being guessed from technical availability.
    """
    return {
        "celestrak": SourceMetadata(
            name="celestrak",
            title="CelesTrak",
            homepage="https://celestrak.org/",
            auth="none",
            status="stable",
            categories=(
                "objects",
                "orbit",
            ),
            host_allowlist=(
                "celestrak.org",
                "www.celestrak.org",
            ),
            description_en=("Satellite catalogue and orbital-element data."),
            description_ko=("위성 카탈로그 및 궤도요소 데이터."),
        ),
        "gcat": SourceMetadata(
            name="gcat",
            title="General Catalog of Artificial Space Objects",
            homepage="https://planet4589.org/space/gcat/",
            auth="none",
            status="stable",
            categories=(
                "objects",
                "physical",
                "mission",
            ),
            host_allowlist=("planet4589.org",),
            description_en=(
                "Catalogue of artificial space objects and related metadata."
            ),
            description_ko=("인공 우주물체와 관련 메타데이터 카탈로그."),
        ),
        "launchlibrary": SourceMetadata(
            name="launchlibrary",
            title="Launch Library 2",
            homepage="https://thespacedevs.com/llapi",
            auth="none",
            status="experimental",
            categories=(
                "launch",
                "mission",
                "objects",
            ),
            host_allowlist=(
                "ll.thespacedevs.com",
                "thespacedevs.com",
            ),
            description_en=(
                "Launch, mission, agency, spacecraft and payload metadata."
            ),
            description_ko=("발사, 임무, 기관, 우주선 및 탑재체 메타데이터."),
        ),
        "noaa": SourceMetadata(
            name="noaa",
            title="NOAA Space Weather Prediction Center",
            homepage="https://www.swpc.noaa.gov/",
            auth="none",
            status="stable",
            categories=(
                "space_weather_series",
                "space_weather_events",
                "solar",
            ),
            host_allowlist=(
                "services.swpc.noaa.gov",
                "www.swpc.noaa.gov",
            ),
            description_en=("Solar and geospace weather products."),
            description_ko=("태양 및 지구우주환경 우주기상 데이터."),
        ),
        "satnogs": SourceMetadata(
            name="satnogs",
            title="SatNOGS DB",
            homepage="https://db.satnogs.org/",
            auth="none",
            status="experimental",
            categories=(
                "objects",
                "orbit",
                "radio",
            ),
            host_allowlist=("db.satnogs.org",),
            description_en=("Open satellite, transmitter and observation metadata."),
            description_ko=("공개 위성, 송신기 및 관측 메타데이터."),
        ),
        "cdaweb": SourceMetadata(
            name="cdaweb",
            title=("NASA SPDF CDAWeb"),
            homepage=("https://cdaweb.gsfc.nasa.gov/"),
            docs_url=("https://cdaweb.gsfc.nasa.gov/hapi"),
            auth="none",
            status="experimental",
            categories=(
                "space_weather_series",
                "solar_wind",
                "geomagnetic",
                "heliophysics",
            ),
            host_allowlist=("cdaweb.gsfc.nasa.gov",),
            description_en=(
                "NASA SPDF CDAWeb HAPI access, "
                "including curated OMNI solar-wind, "
                "IMF and geomagnetic time series."
            ),
            description_ko=(
                "NASA SPDF CDAWeb HAPI 기반 OMNI 태양풍, IMF 및 지자기 시계열 데이터."
            ),
            datasets=(
                DatasetDescriptor(
                    name="omni_hourly",
                    categories=(
                        "solar_wind",
                        "geomagnetic",
                    ),
                    description_en=(
                        "OMNI definitive hourly "
                        "combined IMF, plasma and "
                        "solar/magnetic indices."
                    ),
                    description_ko=(
                        "OMNI 확정 1시간 해상도 IMF, 플라즈마 및 태양/지자기 지수."
                    ),
                ),
                DatasetDescriptor(
                    name="omni_1min",
                    categories=(
                        "solar_wind",
                        "geomagnetic",
                    ),
                    description_en=("OMNI definitive 1-minute high-resolution data."),
                    description_ko=("OMNI 확정 1분 고해상도 데이터."),
                ),
                DatasetDescriptor(
                    name="omni_5min",
                    categories=(
                        "solar_wind",
                        "geomagnetic",
                    ),
                    description_en=("OMNI definitive 5-minute high-resolution data."),
                    description_ko=("OMNI 확정 5분 고해상도 데이터."),
                ),
            ),
            policy=SourcePolicy(),
        ),
        "lisird": SourceMetadata(
            name="lisird",
            title=("LASP LISIRD"),
            homepage=("https://lasp.colorado.edu/lisird/"),
            docs_url=("https://lasp.colorado.edu/lisird/latis/hapi"),
            auth="none",
            status="experimental",
            categories=(
                "solar",
                "solar_irradiance",
                "space_weather_series",
            ),
            host_allowlist=("lasp.colorado.edu",),
            description_en=(
                "LASP LISIRD HAPI solar irradiance and solar-index time series."
            ),
            description_ko=("LASP LISIRD HAPI 기반 태양복사 및 태양지수 시계열."),
            datasets=(
                DatasetDescriptor(
                    name="eve_bands",
                    categories=(
                        "solar_irradiance",
                        "euv",
                    ),
                ),
                DatasetDescriptor(
                    name="eve_lines",
                    categories=(
                        "solar_irradiance",
                        "euv",
                    ),
                ),
                DatasetDescriptor(
                    name="timed_see_lines",
                    categories=(
                        "solar_irradiance",
                        "euv",
                    ),
                ),
                DatasetDescriptor(
                    name="timed_see_xps",
                    categories=(
                        "solar_irradiance",
                        "xuv",
                    ),
                ),
                DatasetDescriptor(
                    name="mgii",
                    categories=(
                        "solar",
                        "proxy",
                    ),
                ),
                DatasetDescriptor(
                    name="solar_radio",
                    categories=(
                        "solar",
                        "proxy",
                    ),
                ),
            ),
            policy=SourcePolicy(),
        ),
        "wdc_kyoto": SourceMetadata(
            name="wdc_kyoto",
            title=("WDC for Geomagnetism, Kyoto"),
            homepage=("https://wdc.kugi.kyoto-u.ac.jp/"),
            docs_url=("https://wdc.kugi.kyoto-u.ac.jp/hapi/"),
            auth="none",
            status="experimental",
            categories=(
                "geomagnetic",
                "space_weather_series",
            ),
            host_allowlist=("wdc.kugi.kyoto-u.ac.jp",),
            description_en=(
                "Geomagnetic indices from the "
                "World Data Center for Geomagnetism, "
                "Kyoto, through HAPI."
            ),
            description_ko=(
                "교토 세계지자기데이터센터의 "
                "Dst, AE, ASY/SYM, Kp/ap 등 "
                "HAPI 지자기 지수."
            ),
            datasets=(
                DatasetDescriptor(
                    name="dst_hourly",
                    categories=(
                        "geomagnetic",
                        "dst",
                    ),
                ),
                DatasetDescriptor(
                    name="ae_hourly",
                    categories=(
                        "geomagnetic",
                        "ae",
                    ),
                ),
                DatasetDescriptor(
                    name="ae_minute",
                    categories=(
                        "geomagnetic",
                        "ae",
                    ),
                ),
                DatasetDescriptor(
                    name="asysym_minute",
                    categories=(
                        "geomagnetic",
                        "asysym",
                    ),
                ),
                DatasetDescriptor(
                    name="kp_ap_3hour",
                    categories=(
                        "geomagnetic",
                        "kp",
                        "ap",
                    ),
                ),
                DatasetDescriptor(
                    name="ap_daily",
                    categories=(
                        "geomagnetic",
                        "ap",
                    ),
                ),
            ),
            policy=SourcePolicy(
                terms_url=("https://wdc.kugi.kyoto-u.ac.jp/wdc/Sec3.html"),
                citation_required=True,
                commercial_use="restricted",
                redistribution="unknown",
            ),
        ),
        "spacetrack": SourceMetadata(
            name="spacetrack",
            title="Space-Track.org",
            homepage="https://www.space-track.org/",
            auth="account",
            status="restricted",
            categories=(
                "objects",
                "orbit",
            ),
            host_allowlist=(
                "www.space-track.org",
                "space-track.org",
            ),
            description_en=(
                "Authenticated space-object catalogue and orbital history."
            ),
            description_ko=("인증이 필요한 우주물체 카탈로그 및 과거 궤도 데이터."),
        ),
    }


def source_metadata(name: str) -> SourceMetadata:
    try:
        return builtin_source_metadata()[name]
    except KeyError as exc:
        raise KeyError(f"No built-in source metadata for {name!r}") from exc
