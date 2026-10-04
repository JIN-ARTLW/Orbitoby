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
            title=("NOAA Space Weather Prediction Center"),
            homepage=("https://www.swpc.noaa.gov/"),
            docs_url=("https://www.swpc.noaa.gov/products-and-data"),
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
            description_en=(
                "Solar and geospace weather "
                "products including rolling "
                "GOES and real-time solar-wind "
                "measurements."
            ),
            description_ko=(
                "GOES 및 실시간 태양풍 자료를 포함한 태양·지구우주환경 우주기상 데이터."
            ),
            datasets=(
                DatasetDescriptor(
                    name="goes_xray_1day",
                    categories=(
                        "solar",
                        "space_weather_series",
                    ),
                ),
                DatasetDescriptor(
                    name=("goes_xray_flares_7day"),
                    categories=(
                        "solar",
                        "space_weather_events",
                    ),
                ),
                DatasetDescriptor(
                    name=("goes_integral_protons_1day"),
                    categories=(
                        "solar",
                        "particles",
                    ),
                ),
                DatasetDescriptor(
                    name="goes_euvs_1day",
                    categories=(
                        "solar",
                        "space_weather_series",
                    ),
                ),
                DatasetDescriptor(
                    name="rtsw_mag_1m",
                    categories=(
                        "solar_wind",
                        "space_weather_series",
                    ),
                ),
                DatasetDescriptor(
                    name="rtsw_wind_1m",
                    categories=(
                        "solar_wind",
                        "space_weather_series",
                    ),
                ),
            ),
        ),
        "donki": SourceMetadata(
            name="donki",
            title=("NASA Space Weather DONKI"),
            homepage=("https://ccmc.gsfc.nasa.gov/DONKI/"),
            docs_url=("https://ccmc.gsfc.nasa.gov/tools/DONKI/"),
            auth="none",
            status="stable",
            categories=(
                "space_weather_events",
                "solar",
                "solar_wind",
                "geomagnetic",
            ),
            host_allowlist=("ccmc.gsfc.nasa.gov",),
            description_en=(
                "NASA DONKI event, analysis, "
                "model and notification data for "
                "space-weather activity."
            ),
            description_ko=("NASA DONKI의 우주기상 사건, 분석, 모델 및 알림 데이터."),
            datasets=(
                DatasetDescriptor(
                    name="cme",
                    categories=(
                        "solar",
                        "space_weather_events",
                    ),
                ),
                DatasetDescriptor(
                    name="cme_analysis",
                    categories=(
                        "solar",
                        "space_weather_events",
                    ),
                ),
                DatasetDescriptor(
                    name="geomagnetic_storm",
                    categories=(
                        "geomagnetic",
                        "space_weather_events",
                    ),
                ),
                DatasetDescriptor(
                    name="solar_flare",
                    categories=(
                        "solar",
                        "space_weather_events",
                    ),
                ),
                DatasetDescriptor(
                    name="sep",
                    categories=(
                        "solar",
                        "particles",
                        "space_weather_events",
                    ),
                ),
                DatasetDescriptor(
                    name="high_speed_stream",
                    categories=(
                        "solar_wind",
                        "space_weather_events",
                    ),
                ),
            ),
            policy=SourcePolicy(
                terms_url=("https://api.nasa.gov/"),
                citation_required=None,
                commercial_use="unknown",
                redistribution="unknown",
            ),
        ),
        "gfz": SourceMetadata(
            name="gfz",
            title="GFZ Geomagnetic Indices",
            homepage="https://kp.gfz.de/en",
            docs_url="https://kp.gfz.de/en/data",
            auth="none",
            status="stable",
            categories=(
                "space_weather_series",
                "geomagnetic",
                "solar",
            ),
            host_allowlist=("kp.gfz.de",),
            description_en=(
                "Official Kp and derived geomagnetic "
                "indices, Hpo indices, and selected "
                "solar indices from GFZ."
            ),
            description_ko=(
                "GFZ의 공식 Kp 및 파생 지자기 지수, Hpo 지수와 일부 태양 지수."
            ),
            datasets=(
                DatasetDescriptor(
                    name="kp",
                    categories=("geomagnetic",),
                ),
                DatasetDescriptor(
                    name="ap",
                    categories=("geomagnetic",),
                ),
                DatasetDescriptor(
                    name="ap_daily",
                    categories=("geomagnetic",),
                ),
                DatasetDescriptor(
                    name="hp30",
                    categories=("geomagnetic",),
                ),
                DatasetDescriptor(
                    name="hp60",
                    categories=("geomagnetic",),
                ),
                DatasetDescriptor(
                    name="f107_observed",
                    categories=("solar",),
                ),
                DatasetDescriptor(
                    name="f107_adjusted",
                    categories=("solar",),
                ),
            ),
            policy=SourcePolicy(
                license_name="CC BY 4.0",
                license_url=("https://creativecommons.org/licenses/by/4.0/"),
                terms_url=("https://kp.gfz.de/en/about-kp"),
                citation_required=True,
                commercial_use="allowed",
                redistribution="allowed",
            ),
        ),
        "silso": SourceMetadata(
            name="silso",
            title=("WDC-SILSO Sunspot Number"),
            homepage=("https://www.sidc.be/SILSO/"),
            docs_url=("https://www.sidc.be/SILSO/datafiles"),
            auth="none",
            status="stable",
            categories=(
                "space_weather_series",
                "solar",
            ),
            host_allowlist=(
                "www.sidc.be",
                "sidc.be",
            ),
            description_en=("International Sunspot Number Version 2 from WDC-SILSO."),
            description_ko=("WDC-SILSO 국제 흑점수 Version 2 데이터."),
            datasets=(
                DatasetDescriptor(
                    name="sunspot_daily",
                    categories=("solar",),
                ),
                DatasetDescriptor(
                    name="sunspot_monthly",
                    categories=("solar",),
                ),
                DatasetDescriptor(
                    name=("sunspot_monthly_smoothed"),
                    categories=("solar",),
                ),
            ),
            policy=SourcePolicy(
                license_name=("CC BY-NC 4.0"),
                license_url=("https://creativecommons.org/licenses/by-nc/4.0/"),
                terms_url=("https://www.sidc.be/SILSO/aboutSILSO"),
                citation_required=True,
                commercial_use="restricted",
                redistribution="allowed",
            ),
        ),
        "nrcan": SourceMetadata(
            name="nrcan",
            title=("Space Weather Canada / DRAO F10.7"),
            homepage=(
                "https://spaceweather.gc.ca/"
                "forecast-prevision/solar-solaire/"
                "solarflux/sx-en.php"
            ),
            docs_url=(
                "https://spaceweather.gc.ca/"
                "forecast-prevision/solar-solaire/"
                "solarflux/sx-3-en.php"
            ),
            auth="none",
            status="stable",
            categories=(
                "space_weather_series",
                "solar",
            ),
            host_allowlist=(
                "spaceweather.gc.ca",
                "www.spaceweather.gc.ca",
            ),
            description_en=(
                "Canadian 10.7 cm solar radio flux "
                "measurements with observed, "
                "1-AU-adjusted, and URSI Series D "
                "values."
            ),
            description_ko=(
                "캐나다 10.7 cm 태양 전파 플럭스 "
                "측정값으로 관측값, 1 AU 보정값, "
                "URSI Series D 값을 제공."
            ),
            datasets=(
                DatasetDescriptor(
                    name="f107_measurements",
                    categories=(
                        "solar",
                        "space_weather_series",
                    ),
                    description_en=(
                        "Current NRCan/DRAO F10.7 "
                        "measurement archive from "
                        "2004-10-28 onward."
                    ),
                    description_ko=("2004-10-28 이후 NRCan/DRAO F10.7 관측 아카이브."),
                ),
                DatasetDescriptor(
                    name="f107_legacy_daily_1947_1996",
                    categories=(
                        "solar",
                        "space_weather_series",
                    ),
                    description_en=(
                        "Legacy official-domain daily "
                        "F10.7 artifact covering the "
                        "historical 1947-1996 era."
                    ),
                    description_ko=(
                        "1947-1996 시기의 공식 도메인 레거시 일별 F10.7 자료."
                    ),
                ),
                DatasetDescriptor(
                    name=("f107_legacy_measurements_1996_2007"),
                    categories=(
                        "solar",
                        "space_weather_series",
                    ),
                    description_en=(
                        "Legacy official-domain "
                        "multi-daily F10.7 measurements "
                        "for the 1996-2007 era."
                    ),
                    description_ko=(
                        "1996-2007 시기의 공식 도메인 레거시 다회 F10.7 관측 자료."
                    ),
                ),
            ),
            policy=SourcePolicy(
                terms_url=("https://www.canada.ca/en/transparency/terms.html"),
                citation_required=None,
                commercial_use="unknown",
                redistribution="unknown",
            ),
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
        "swarm": SourceMetadata(
            name="swarm",
            title="ESA Swarm / VirES",
            homepage="https://vires.services/",
            docs_url="https://vires.services/hapi/",
            auth="none",
            status="experimental",
            categories=(
                "thermosphere",
                "density",
                "earth_observation",
            ),
            host_allowlist=("vires.services",),
            description_en=(
                "ESA Swarm thermospheric mass-density "
                "observations accessed through the "
                "VirES HAPI service."
            ),
            description_ko=(
                "VirES HAPI를 통해 제공되는 ESA Swarm 열권 질량밀도 관측 자료."
            ),
            datasets=(
                DatasetDescriptor(
                    name="density_a_acc",
                    categories=(
                        "thermosphere",
                        "density",
                    ),
                    description_en=(
                        "Swarm A thermospheric density "
                        "derived from accelerometer and "
                        "precise-orbit data."
                    ),
                    description_ko=(
                        "가속도계와 정밀궤도 자료로부터 산출된 Swarm A 열권 밀도."
                    ),
                ),
                DatasetDescriptor(
                    name="density_b_acc",
                    categories=(
                        "thermosphere",
                        "density",
                    ),
                    description_en=(
                        "Swarm B thermospheric density "
                        "derived from accelerometer and "
                        "precise-orbit data."
                    ),
                    description_ko=(
                        "가속도계와 정밀궤도 자료로부터 산출된 Swarm B 열권 밀도."
                    ),
                ),
                DatasetDescriptor(
                    name="density_c_acc",
                    categories=(
                        "thermosphere",
                        "density",
                    ),
                    description_en=(
                        "Swarm C thermospheric density "
                        "derived from accelerometer and "
                        "precise-orbit data."
                    ),
                    description_ko=(
                        "가속도계와 정밀궤도 자료로부터 산출된 Swarm C 열권 밀도."
                    ),
                ),
                DatasetDescriptor(
                    name="density_a_pod",
                    categories=(
                        "thermosphere",
                        "density",
                    ),
                    description_en=(
                        "Swarm A thermospheric density "
                        "derived from precise-orbit data "
                        "only."
                    ),
                    description_ko=("정밀궤도 자료만으로 산출된 Swarm A 열권 밀도."),
                ),
                DatasetDescriptor(
                    name="density_b_pod",
                    categories=(
                        "thermosphere",
                        "density",
                    ),
                    description_en=(
                        "Swarm B thermospheric density "
                        "derived from precise-orbit data "
                        "only."
                    ),
                    description_ko=("정밀궤도 자료만으로 산출된 Swarm B 열권 밀도."),
                ),
                DatasetDescriptor(
                    name="density_c_pod",
                    categories=(
                        "thermosphere",
                        "density",
                    ),
                    description_en=(
                        "Swarm C thermospheric density "
                        "derived from precise-orbit data "
                        "only."
                    ),
                    description_ko=("정밀궤도 자료만으로 산출된 Swarm C 열권 밀도."),
                ),
            ),
            policy=SourcePolicy(
                terms_url=("https://vires.services/data_terms"),
                citation_required=True,
                commercial_use="unknown",
                redistribution="restricted",
            ),
        ),
        "discos": SourceMetadata(
            name="discos",
            title="ESA DISCOS",
            homepage=("https://discosweb.esoc.esa.int/"),
            docs_url=("https://discosweb.esoc.esa.int/"),
            auth="token",
            status="restricted",
            categories=(
                "objects",
                "physical_properties",
                "space_debris",
            ),
            host_allowlist=("discosweb.esoc.esa.int",),
            description_en=(
                "Authenticated ESA DISCOS "
                "space-object metadata including "
                "physical characteristics, "
                "registration and launch-related "
                "information."
            ),
            description_ko=(
                "인증을 통해 접근하는 ESA DISCOS "
                "우주물체 메타데이터로 질량, 형상, "
                "치수, 등록 및 발사 관련 정보를 제공."
            ),
            datasets=(
                DatasetDescriptor(
                    name="objects",
                    categories=(
                        "objects",
                        "physical_properties",
                    ),
                    description_en=(
                        "DISCOS object records queried by NORAD or DISCOS identifier."
                    ),
                    description_ko=(
                        "NORAD 또는 DISCOS 식별자로 조회하는 우주물체 레코드."
                    ),
                ),
            ),
            policy=SourcePolicy(
                citation_required=True,
                commercial_use="unknown",
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
