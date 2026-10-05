# Orbitoby

<p align="center">
  <img src="docs/assets/orbitoby_banner.png" alt="Toby, the Orbitoby mascot">
</p>

**Orbitoby core never guesses the data.**

Orbitoby는 우주환경·위성 궤도 연구를 위한 provenance-first Python 패키지입니다. 원본 수집, canonical 시계열, exact-time 정렬, catalogue·historical orbit, Swarm 밀도 및 명시적 NRLMSIS 계산을 연결합니다. v0.1.1은 현재 공개된 alpha release입니다.

Orbitoby is a provenance-first Python toolkit for space-weather and orbital research. It connects raw acquisition, canonical time series, exact-time alignment, catalogues, historical orbit, Swarm density and explicit NRLMSIS evaluation. Version 0.1.1 is the current public alpha release.

## 설치 / Installation

Python ≥3.12. Orbitoby는 PyPI에서 직접 설치할 수 있습니다.

Use Python ≥3.12. Orbitoby can be installed directly from PyPI.

```bash
python -m pip install orbitoby
python -m pip install "orbitoby[models]"
```

`[models]`는 pymsis를 추가합니다. 기본 탐색·시계열·저장·SVG 플롯에는 필요하지 않습니다. 설치형 CLI entry point는 제공하지 않습니다.

The models extra adds pymsis; base discovery, time series, storage and SVG plotting do not require it. No installed CLI entry point is provided.

## Archive 빠른 시작 / Quick start

```python
from orbitoby import Archive

with Archive() as archive:
    print(archive.sources_available())
    print(archive.datasets(metric="kp", live=False))
    info = archive.dataset_info("gfz", "kp")
    kp = archive.timeseries(
        "kp", source="gfz", dataset="kp", start="2024-05-10", end="2024-05-11"
    )
    archive.plot(kp, kind="scatter", title="GFZ Kp").save("kp.svg")
    window = archive.window(
        fields=["kp", "ap"], source="gfz", start="2024-05-10", end="2024-05-11"
    )
    print(window.data, window.presence)
```

`datasets()`·`dataset_info()`는 정적 또는 명시적 `live=True` 탐색을 지원합니다. provider-native 자료는 `fetch()`로, 지원된 canonical metric은 `timeseries()` 또는 `space_weather()`로 조회합니다. 모든 provider-native dataset에 canonical mapping이 있는 것은 아닙니다.

Discovery is static unless live lookup is requested. Use fetch() for provider-native data and timeseries()/space_weather() for supported canonical metrics. Native dataset support does not imply canonical mapping.

## 과학적 의미 / Scientific semantics

Canonical 조회와 window는 UTC `[start,end)`입니다. ResearchWindow는 실제 timestamp의 합집합에 exact 정렬하고 `data`, `presence`, `missing_reason`, `provenance`, `units`를 반환합니다. 중복 metric/timestamp는 오류이며 결측값을 보간·평활·resample·ffill·bfill하지 않습니다. 플롯은 line/scatter SVG와 원 데이터·provenance를 반환합니다.

Canonical queries/windows use UTC [start,end). ResearchWindow aligns the union of actual timestamps and retains values, presence, missing reasons, provenance and units. Duplicate claims raise errors. There is no interpolation, smoothing, resampling or filling. Native plotting returns line/scatter SVG, data and provenance.

source가 모호하면 명시해야 합니다. `source_preference`는 첫 matching binding을 선택하며 장애 시 다른 source로 자동 fallback하지 않습니다. 기본 `artifact_resolution="all"`은 중복 주장을 보존합니다. 명시적 `preferred`는 우선순위 선택일 뿐 과학적 충돌 해결이 아닙니다. NRCan의 선언된 같은-source mergeable 제품은 함께 반환될 수 있습니다.

Ambiguous sources require selection. Source preference selects the first matching binding, not runtime outage fallback. Default artifact resolution preserves claims; explicitly requested preferred selection is a priority policy, not scientific adjudication. Declared mergeable products within NRCan can be returned together.

## Population과 historical orbit / Population and orbit

```python
with Archive(allow_dotenv=True) as archive:
    candidates = archive.objects(
        start="2024-05-10",
        end="2024-05-11",
        existence="throughout",
        object_type="payload",
        sync=True,
    )
    orbit = archive.orbit(norad_id=39452, start="2024-05-10", end="2024-05-11")
    summary = archive.orbit_summary(
        [39452],
        start="2024-05-10",
        end="2024-05-11",
        periapsis_km=(200, 2000),
        min_coverage=1.0,
        sync=False,
    )
```

기간 population은 전체 CelesTrak SATCAT의 launch/decay assertion으로 조회합니다. 기본 객체 검색은 로컬이며 `sync=True`로 SATCAT을 갱신합니다. historical orbit은 사용자 credential이 필요한 Space-Track GP_HISTORY이고 날짜 `[start,end)`입니다. 요약 coverage는 실제 레코드가 존재하는 날짜 비율이며 연속 관측을 뜻하지 않습니다.

Period population applies launch/decay assertions from complete CelesTrak SATCAT. Default object searches are local; sync=True refreshes SATCAT. Historical orbit uses authenticated Space-Track GP_HISTORY with date-based [start,end). Summary coverage is the fraction of dates with records, not continuous observation.

## Swarm와 MSIS / Swarm and MSIS

Swarm A/B/C ACC·POD는 관측 기반 provider-derived 밀도이고 NRLMSIS 2.1은 별도 model_output입니다. trajectory는 UTC timestamp·경도/위도 degree·고도 km와 실제 provenance를 제공해야 합니다.

Swarm A/B/C ACC/POD are observation-derived provider products; NRLMSIS 2.1 is separate model output. Supply trajectory UTC timestamps, longitude/latitude in degrees, altitude in kilometres and real provenance.

```python
# trajectory와 trajectory_parents 구성은 실행 예제를 참고하세요.
# See the runnable example for trajectory and real parent construction.
inputs, parents = archive.msis_inputs(
    trajectory, driver_source="gfz", trajectory_parents=trajectory_parents
)
modeled = archive.msis_density(inputs, parents=parents)
comparison = observed.merge(
    modeled,
    on="timestamp",
    how="outer",
    suffixes=("_observed", "_model"),
    validate="one_to_one",
    indicator=True,
)
```

`msis_inputs()`는 명시적으로 GFZ를 선택해 이전 일 F10.7, 완전한 중심 81일 평균, 지정 Ap vector를 구성합니다. 필수 day/bin 누락과 중복 유효 forcing은 오류입니다. 모델 정의 평균은 관측 보간이 아니며 중심 평균은 미래 정보를 사용합니다. 모델 output은 backend/version·parameters·parent lineage를 저장합니다.

Explicit GFZ forcing construction requires the previous-day F10.7, complete centered 81-day mean and defined Ap vector. Missing bins/days and duplicate valid drivers fail. Model-defined means are not observation interpolation; centered means use future information. Model output records versions, parameters and parent lineage.

## 저장·확장 / Storage and extensions

기본 저장소는 `~/.orbitoby`; import 전 `ORBITOBY_DATA_DIR`로 변경합니다. raw payload/manifest/SHA-256, DuckDB metadata, canonical Parquet와 derived/model Parquet를 분리하고 artifact·lineage로 연결합니다. `artifacts()`, `coverage()`, `product_store.lineage()`로 조사합니다.

The default archive is ~/.orbitoby, overridable before import. Raw payloads/manifests/hashes, DuckDB metadata and canonical/derived/model Parquet are separate and linked by artifact IDs and lineage.

HTTPS JSON/CSV/TSV declarative source를 등록하거나 명시적으로 신뢰한 `orbitoby.sources` Python plugin을 확장할 수 있습니다. canonical binding은 명시적으로 정의해야 하며 plugin은 사용자 권한으로 실행됩니다. credential은 runtime/keyring/environment/Colab/opt-in dotenv에서 해석하고 import만으로 .env를 로드하지 않습니다.

Extensions include declarative HTTPS JSON/CSV/TSV and explicitly trusted Python source plugins. Canonical bindings must be explicit; plugins run with user permissions. Credential resolution supports runtime/keyring/environment/Colab/opt-in dotenv without implicit .env loading on import.

## 실행 예제와 연결 검사 / Workflow and connection check

저장소 root에서 순차 실행하세요. 예제는 전체 population→명시적 1개 위성의 historical orbit→F10.7/Kp/Ap/Dst/solar wind→Swarm→MSIS→exact 비교를 시연합니다. 실패 단계는 분리해서 보고합니다.

Run sequentially from the repository root. The example demonstrates complete population, one explicitly selected historical orbit, weather indices, Swarm, MSIS and exact comparison, reporting stage failures separately.

```bash
.venv/bin/python examples/science_day.py --allow-dotenv
.venv/bin/python scripts/check_connections.py --allow-dotenv
```

연결 검사는 source 수·API·DB/storage와 주요 provider를 PASS/FAIL/SKIP으로 표시하며 secrets를 출력하지 않습니다. credential 미설정은 SKIP, FAIL이 있으면 exit 1입니다. `--offline`, `--timeout 20`도 지원합니다. 연결 성공은 자료 전체의 완전성 인증이 아닙니다.

Diagnostics report registry, APIs, local storage and key providers without secrets. Missing credentials are SKIP; any FAIL exits 1. Offline mode and per-worker timeout are available. Connectivity does not certify scientific completeness.

## 제약·문서·인용 / Limits, documentation and citation

현재 snapshot의 과거 존재 판정은 당시 catalogue 복원이 아닙니다. 결측 물리/임무 metadata, quality flag, provider revision, GP ID 중복, cache freshness를 사용자가 검토해야 합니다. orbit propagation·항력/인과적 decay·자동 cohort·범용 CLI는 제공하지 않습니다. E2E 성공과 과학적 타당성 검증은 구별합니다.

Retrospective existence from a current snapshot is not a historical catalogue reconstruction. Researchers must assess missing metadata, quality, revisions, GP-ID deduplication and cache freshness. Propagation, drag/causal decay, automatic cohorts and a general CLI are outside this release. E2E success is distinct from scientific validation.

- [한·영 위키 / Bilingual wiki](https://jin-artlw.github.io/Orbitoby/)
- [전체 공개 API와 dataset / Complete inventory](https://jin-artlw.github.io/Orbitoby/api-inventory/)
- [연구 예제 코드 / Research example](examples/science_day.py)
- [검증 보고서 / Verification report](docs/RELEASE_0_1_1_REPORT.md)
- [기능 동결 / Feature freeze](docs/adr/2026-10-04-release-freeze.md)

소프트웨어 인용: Jin Yeseo, Orbitoby, 사용 버전과 [저장소](https://github.com/JIN-ARTLW/Orbitoby). dataset·model 문헌은 별도로 인용하세요. 확인되지 않은 DOI는 제시하지 않습니다. 코드 라이선스는 [Apache-2.0](LICENSE), 자산·외부 자료 구분은 [NOTICE](NOTICE)를 따릅니다.

Cite Jin Yeseo, Orbitoby, the version used and the repository, plus original datasets and models. No unverified DOI is supplied. Code is Apache-2.0; NOTICE distinguishes assets and external materials.
