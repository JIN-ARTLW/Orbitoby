좋아. 기존 `ORBITOBY_MASTER_PLAN.md`를 버리는 게 아니라, 그 위에 **“Orbitoby 소프트웨어 + 실제 연구 논문 + 학술적 공개/검증까지 모두 끝난 상태”를 정의하는 최상위 Master Plan v2.0**을 얹는 방식으로 잡자.

기존 계획은 이미 `raw/provenance → source architecture → credential/plugin → canonical warehouse → identity → research API → derived layer → Colab → PyPI`라는 기본 뼈대를 가지고 있고, 기존 데이터와 기능을 버리지 않는 방향으로 설계돼 있다. 여기서는 그 구조를 **제품 완성도, 연구 완성도, 논문, 재현성, 학술적 인정, 장기 유지보수까지** 확장한다.

# Orbitoby Ultimate Master Plan v2.0

## 0. 최종 목적

최종 상태의 Orbitoby는 단순히 “여러 사이트에서 데이터를 받아주는 Python 패키지”가 아니다.

> **Orbitoby = 우주물체와 우주환경 데이터를 신뢰 가능한 출처에서 수집하고, 원본을 보존하고, 객체를 식별·통합하고, 시간축으로 결합하고, 연구 가능한 형태로 파생·조회·시각화·내보내며, 그 모든 과정의 출처와 재현성을 보장하는 연구용 데이터 인프라.**

그리고 프로젝트 전체는 두 개의 독립적인 결과물을 가져야 한다.

|트랙|최종 결과|
|---|---|
|**Software Track**|Orbitoby `v1.0.0`, PyPI, DOI, 문서, 테스트, 공개개발, software paper|
|**Research Track**|태양활동–열권밀도–LEO 궤도감쇠 연구 논문 + 완전한 재현성 패키지|

둘은 서로 연결되지만 분리한다.

```
Orbitoby
= 범용 연구 소프트웨어

2026-scienceday
= Orbitoby를 실제 연구에 사용하는 첫 reference study
```

이 구분은 앞으로 절대 흐리지 않는 게 좋다.

---

# 1. “정말 완성됐다”의 정의

나는 Orbitoby를 다섯 단계의 완료 게이트로 정의하겠다.

### Gate A — Software Complete

다음이 모두 되어야 한다.

- 모든 핵심 API 구현 완료
- 주요 데이터 영역 통합
- strict source validation
- raw archive + provenance
- source conflicts 보존
- secure auth/plugin system
- canonical DB + migrations
- high-level query
- derived data
- quick-look plotting
- export
- CLI
- Jupyter/Colab
- 문서
- 테스트
- CI/security
- PyPI
- Zenodo DOI

### Gate B — Research Complete

Orbitoby만을 이용해 실제 위성 연구 데이터를 처음부터 구축하고 분석할 수 있어야 한다.

현재 Science Day 기준 연구 파이프라인은 이미 `orbit + physical + space_weather`를 동일 window로 가져오고 F10.7, SSN, Kp, ap/Ap, Dst, AE, 질량·형상·면적, MSIS density 등을 대상으로 잡고 있다.

### Gate C — Reproducibility Complete

제3자가 새 컴퓨터에서:

```
git clone ...
uv sync
```

한 뒤 정해진 명령/노트북을 따라가면 **논문의 주요 표와 그림을 다시 생성할 수 있어야 한다.**

### Gate D — Scholarly Complete

- Orbitoby DOI
- 연구 논문 제출
- 연구 데이터/코드 보존
- Orbitoby 자체 software paper 제출
- citation metadata 완료

까지.

### Gate E — Mature/Open-source Complete

- `v1.0.0`
- public API stability
- 외부 사용자 검증
- 실제 issue/feedback 반영
- 유지보수 정책
- source health monitoring
- deprecation 정책

까지.

**A~E를 모두 통과하면 “Orbitoby 프로젝트를 높은 수준으로 완성했다”고 부를 수 있다.**

논문 심사 결과는 외부 변수이므로 우리가 통제할 수 있는 최종 상태는 **논문 제출 + software-paper 제출**이다. 그 이후 두 논문까지 accept/publish되면 “externally validated / 최종의 최종 종료” 상태로 본다.

---

# 2. 제품 범위 — 최종 Orbitoby가 가져야 하는 기능

## 2.1 Source Layer

최종적으로 세 종류를 모두 지원한다.

```
Built-in trusted sources
        +
Persistent user sources
        +
Third-party plugins
```

이 원칙은 기존 계획의 핵심 설계와 일치한다.

### Built-in source 상태

모든 source는 다음 상태 중 하나다.

```
candidate
experimental
stable
restricted
deprecated
removed
```

`stable`이 되려면 단순히 API 호출 성공으로 끝나지 않는다.

기존 계획의 기준대로 공식 문서, 약관/라이선스, 인증, rate policy, metadata, parser, canonical normalization, provenance, coverage/cache, fixture test, live smoke test, 429/5xx 처리, secret redaction, citation/license report까지 모두 검증한다.

### 최종 built-in 우선군

```
Orbital / object
├─ Space-Track
├─ CelesTrak
├─ GCAT
├─ ESA DISCOS
└─ SatNOGS

Launch / mission
├─ Launch Library 2
├─ GCAT
└─ DISCOS

Space weather / solar
├─ NOAA SWPC
├─ NASA SPDF / CDAWeb / OMNI / HAPI
├─ NASA DONKI
├─ GFZ Kp / ap / Ap
├─ NRCan / Canada F10.7
├─ WDC Kyoto
└─ SILSO
```

새 source는 “유명하다”가 아니라 **사용가치 + 데이터 품질 + 기계 접근성 + provenance + 라이선스**를 모두 통과해야 한다.

---

# 3. Canonical Data Model

웹사이트 이름을 기준으로 DB를 만들지 않는다.

최종 canonical domain은:

```
objects
identifiers
aliases

orbit
physical
mission
launch
radio
reentry

space_weather_series
space_weather_events

derived

provenance
source_records
licenses
coverage
```

### Identity

객체 하나에는 내부적으로:

```
object_uid
```

를 부여한다.

연결 우선순위는:

```
NORAD
→ COSPAR
→ trusted provider cross-ID
→ documented launch/piece relation
→ name candidate
```

이름만 비슷하다고 자동 merge하지 않는다.

### Source conflicts

예:

```
DISCOS: mass = 482 kg
GCAT:   mass = 480 kg
```

이면:

```
482를 남기고 480을 버리는 것
```

이 아니라:

```
482 kg — source=DISCOS
480 kg — source=GCAT
```

둘 다 보존한다.

별도의 resolver가 `preferred value`를 만들 수 있지만 원 데이터는 삭제하지 않는다.

이게 Orbitoby의 중요한 연구적 차별점이다.

---

# 4. Raw Archive / Provenance

Orbitoby의 가장 중요한 기반 중 하나다.

모든 fetch는 가능한 경우:

```
request
 ↓
raw response
 ↓
SHA-256
 ↓
manifest
 ↓
normalize
 ↓
canonical record
```

순서로 간다.

Raw artifact는 immutable.

Manifest에는:

```
source
dataset
retrieved_at
content type
adapter version
safe request context
SHA-256
license metadata
```

를 남긴다.

비밀번호, 쿠키, token, Authorization header는 절대 남기지 않는다.

---

# 5. Historical Coverage Engine

현재 구현되어 있는 Space-Track 방식이 기준 모델이다.

예:

```
DB coverage
2020-01-01 ~ 2020-01-31

requested
2020-01-15 ~ 2020-02-29
```

이면:

```
2020-02-01 ~ 2020-02-29
```

만 가져온다.

이 시스템을 모든 historical source로 일반화한다.

각 source에는:

```
cache_ttl
historical_immutable
revision_window
provisional_window
refresh_interval
max_query_span
```

을 둔다.

---

# 6. Authentication

사용자가 account를 직접 쓰되 사용은 최대한 간단하게 만든다.

```
orbitoby auth set spacetrack
```

그러면 hidden prompt.

저장 우선순위:

```
explicit runtime credential
→ OS keyring
→ environment variables
→ Colab Secrets
→ .env development compatibility
```

사용자 credential은 Orbitoby repo나 archive에 절대 저장하지 않는다.

---

# 7. Network Security

모든 built-in adapter는 하나의 공통 secure HTTP layer를 쓴다.

필수:

```
TLS verification
timeout
host allowlist
redirect validation
response-size limit
rate limiter
Retry-After
exponential backoff
429 handling
5xx circuit/backoff
secret redaction
cache-first request
Orbitoby User-Agent
```

보안을 이유로 정상 기능을 없애지 않되, 위험한 동작은 explicit opt-in만 허용한다.

---

# 8. User Source System

이 부분은 Orbitoby의 장기 확장성에서 아주 중요하다.

### Level 1 — Low-code

```
archive.add_http_source(
    ...
)
```

JSON / CSV / TSV 수준이면 사용자가 adapter 클래스를 만들 필요가 없게 한다.

### Level 2 — Python Adapter

```
class MySource(SourceAdapter):
    ...
```

복잡한 pagination/auth/schema 대응.

### Level 3 — External plugin

```
pip install orbitoby-my-source
```

그리고 Python entry point로 자동 발견.

단, **발견 ≠ 실행 허가**.

Python plugin은 최초 한 번 trust를 받아야 한다.

---

# 9. Public API

최종 사용자 경험은 복잡하면 안 된다.

```
from orbitoby import Archive

archive = Archive()
```

그리고 핵심은:

```
archive.fetch()
archive.object()
archive.orbit()
archive.space_weather()
archive.window()
archive.timeseries()
archive.search()
archive.derive()
```

이다.

---

# 10. Result Object

단순 DataFrame만 던지고 끝내지 않는다.

최종적으로:

```
result.data
result.meta
result.provenance
result.sources
result.credits()
result.license_report()

result.to_pandas()
result.to_csv()
result.to_parquet()

result.plot()
```

같은 얇은 result layer를 둔다.

필요하면 DataFrame을 바로 받을 수도 있게 한다.

---

# 11. Quick-look Plotting

이건 정식 기능으로 넣는 게 좋다.

하지만 시각화 라이브러리를 새로 만들지는 않는다.

```
archive.timeseries(...).plot()
```

이면 시간축 line plot.

규칙:

```
1 variable
→ one line

multiple variables, same units
→ same axes

multiple variables, incompatible units
→ separate panels

missing values
→ 그대로 표시

automatic interpolation
→ 절대 안 함
```

옵션도 최소한:

```
.plot()
.plot(fields=[...])
.plot(title="...")
```

까지만.

논문용 고급 figure는 사용자가 pandas + matplotlib 등으로 만든다.

---

# 12. Derived Science Layer

Orbitoby를 단순 API wrapper와 구분하는 핵심 중 하나다.

```
altitude
orbital period
semimajor axis
apogee/perigee

orbital decay rate
rolling decay metrics

MSIS density

drag-related quantities
ballistic/drag parameter transforms
```

단 모든 derived quantity에는:

```
transform name
transform version
parameters
source records
software version
creation time
```

을 남긴다.

### 관측값과 모델값 구분

예:

```
MSIS density
```

는 절대:

```
observed_density
```

처럼 취급하지 않는다.

`modeled / derived` 상태를 유지한다.

---

# 13. Time-series Engine

Orbitoby의 연구적 핵심.

문제는:

```
TLE/GP → irregular
F10.7 → daily
Kp → 3 h
Dst → hourly
AE → higher cadence
```

처럼 모두 cadence가 다르다는 것.

따라서:

```
archive.timeseries(
    ...,
    cadence="1D",
    alignment={
        "orbit": "nearest",
        "f107": "daily_exact",
        "kp": "aggregate_max",
    },
)
```

처럼 규칙을 사용자가 명시하게 한다.

Orbitoby는 임의로:

```
interpolate
forward fill
resample
```

하지 않는다.

---

# 14. Search Engine

최종적으로:

```
archive.search(
    object_type="PAYLOAD",
    mass_kg=(50, 500),
    altitude_km=(400, 600),
    inclination_deg=(95, 105),
    launch_year=(2015, 2026),
)
```

이 가능해야 한다.

DuckDB/Parquet query pushdown을 이용해서 데이터가 커져도 pandas 전체 로딩을 피한다.

---

# 15. Storage

기준은:

```
Local filesystem
+
DuckDB
+
Parquet
```

이다.

그다음:

```
Google Drive mounted path
fsspec
S3-compatible storage
```

까지 확장할 수 있게 인터페이스만 만든다.

단 **S3나 hosted cloud 서비스 때문에 v1.0을 미루지는 않는다.**

기존 계획에서도 full propagation replacement, desktop GUI, hosted service, 완벽한 arbitrary-code sandbox 등은 v1의 비목표로 잡혀 있다.

---

# 16. GNC / Astrodynamics 연결

Orbitoby 자체가 Orekit/GMAT/STK 대체물이 되어서는 안 된다.

최종 범위는:

```
Orbit data acquisition
Orbit history
Space-environment coupling
Density
Drag
Decay
Basic propagation helper/validation
```

까지.

다음은 **interop 대상**이다.

```
full orbit determination
high-fidelity numerical propagation
covariance propagation
maneuver estimation
guidance
control
```

즉 GNC 연구에 쓰이는 **data/research infrastructure**라는 정체성을 유지한다.

---

# 17. Documentation

최종 공개 문서는 영/한 병기.

필수:

```
README
Getting Started
Installation
Authentication
Sources
Data Model
API Reference
Plugins
User Sources
Security
Licensing
Citation
Colab
Research Examples
Troubleshooting
Contributing
Governance
Changelog
```

가능하면 최종 단계에서는 GitHub Pages/문서 사이트도 둔다.

---

# 18. Software Quality

최종 수준에서는 다음을 목표로 한다.

### Static quality

```
Ruff
type checking
package build
wheel install test
```

### Testing

```
unit
contract
integration
security
migration
live smoke
reproducibility
```

특히 core logic은 가능한 높은 coverage를 유지하되 **coverage 숫자를 올리기 위한 의미 없는 테스트는 만들지 않는다.**

### External API tests

매 PR마다 실제 서버를 때리지 않는다.

```
PR
→ fixture/mock tests

weekly
→ minimal live smoke
```

---

# 19. Security

최종적으로:

```
secret scanning
CodeQL/static analysis
dependency audit
Dependabot
least-privilege GitHub Actions
OIDC PyPI publishing
no long-lived PyPI token
```

을 유지한다.

PyPI 배포 자체는 기존 Master Plan에서도 TestPyPI → GitHub Release → Trusted Publishing/OIDC → provenance/attestation 순으로 설계되어 있다.

---

# 20. Licensing

### Orbitoby

```
Apache-2.0
```

### Toby mascot/photo

```
© JIN-ARTLW
All rights reserved
```

### Data

각 upstream source의 원래 라이선스 그대로.

Export 시:

```
CITATIONS.md
LICENSES.json
```

또는 이에 상응하는 machine-readable manifest를 만든다.

---

# 21. AI Development Provenance

이건 지금부터 반드시 추가하자.

2026년 현재 JOSS는 generative AI를 software/paper 작업에 사용하는 것을 허용하지만, **무슨 도구를 어디에 어떻게 사용했는지, 사람이 모든 결과를 검토·검증했으며 핵심 설계 결정을 내렸다는 disclosure**를 요구한다. [joss.theoj.org](https://joss.theoj.org/about?utm_source=chatgpt.com)

그래서 repo에:

```
AI_USAGE.md
```

를 두는 걸 추천한다.

기록:

```
Tool/model
Date
Purpose
Code/docs/paper area
Human review performed
Validation performed
Final decision maker
```

그리고 중요한 architecture 결정은:

```
docs/adr/
```

에 사람이 직접 판단한 이유를 기록한다.

이건 단순 규정 준수뿐 아니라 **“AI가 코드를 만들었고 사람은 복사만 했다”가 아니라, 네가 문제를 정의하고 설계·검증했다는 증거**가 된다.

---

# 22. v0.1.0 — 첫 완성형 공개 릴리스

이제 범위는 축소하지 않는다.

목표:

> **계획된 Orbitoby의 주요 기능 계열이 전부 처음으로 end-to-end 동작하는 release.**

포함:

```
existing built-ins
all planned research-priority built-ins that pass source admission

raw archive
coverage/cache
provenance

SourceMetadata
SourcePolicy
secure HTTP

credential manager
user sources
plugins
plugin trust

canonical DB
migrations
identity

object
orbit
space_weather
window
timeseries
search
derive

MSIS
decay metrics

plot

export
citations/licenses

CLI
Jupyter
Colab

tests
CI
security
bilingual docs
```

### 0.1.0 종료조건

```
pip install orbitoby
```

가 clean environment에서 성공.

그리고 최소 reference workflow가 모두 돌아가야 한다.

마지막:

```
GitHub v0.1.0 Release
→ PyPI 0.1.0
→ Zenodo
→ DOI
```

Zenodo는 GitHub 저장소를 연결한 뒤 새 release를 ingest/archive할 수 있고, publish된 software record에는 DOI가 발급된다. DOI를 미리 reserve하는 것도 가능하다. [Zenodo](https://help.zenodo.org/docs/deposit/describe-records/reserve-doi/?utm_source=chatgpt.com)

---

# 23. v0.1 이후 버전 전략

`0.1.0` 이후는 “빠진 핵심 기능 추가”가 주가 아니다.

주로:

```
0.1.x
bug/security/source fixes

0.2.x
UX/API refinement
performance
additional vetted datasets

0.3–0.5
research feedback
external-user feedback
advanced provenance/export

0.6–0.8
performance
migration stability
docs maturation

0.9.0
1.0 API candidate

1.0.0
stable public API
```

로 간다.

---

# 24. v1.0.0 Definition of Done

`1.0`은 기능 수가 아니라 **신뢰 계약**이다.

다음이 되어야 한다.

```
API freeze
schema migration stability
documented deprecation rules
source lifecycle policy
plugin API stability
credential API stability
result object stability
provenance contract stability
```

그리고:

```
fresh-install test
Windows/macOS/Linux
Python supported versions
Jupyter
Colab
```

검증.

최소 한 명 이상의 **프로젝트 개발자가 아닌 사용자**가 설치하고 reference workflow를 실행해 보는 것도 강하게 권한다.

---

# 25. Research Paper Track

이제 Science Day 연구는 별도 repo에서 진행한다.

## 연구 핵심 질문

현재 큰 질문:

> 태양활동에 따른 상층대기 밀도 변화가 LEO 인공위성/우주물체의 궤도감쇠에 어떤 영향을 미치며, 그 민감도는 고도와 물체 특성에 따라 어떻게 달라지는가?

### 핵심 chain

```
Solar activity
      ↓
EUV/XUV proxy
      ↓
Thermospheric density
      ↓
Atmospheric drag
      ↓
Orbital energy loss
      ↓
Orbital decay
```

---

# 26. Research Questions

논문에서는 최소 다음을 분리해야 한다.

### RQ1

태양활동 지표와 orbital decay 사이의 관계는 어느 정도인가?

```
F10.7
SSN
```

### RQ2

geomagnetic activity는 어떤 추가 설명력을 가지는가?

```
Kp
ap / Ap
Dst
AE
```

### RQ3

태양·지자기 활동과 modeled thermospheric density 사이의 관계는?

### RQ4

density와 decay 사이의 관계는?

### RQ5

고도에 따라 sensitivity가 어떻게 달라지는가?

### RQ6

mass / effective area / drag-related physical characteristics에 따라 어떻게 달라지는가?

### RQ7

solar-cycle maximum/minimum 및 여러 solar cycle에서 관계가 얼마나 안정적인가?

---

# 27. 연구 설계

논문은 한 번에 regression 하나 돌리고 끝내면 안 된다.

### Level 1 — Baseline reproduction

Ashruf류 접근과 비교 가능한 지표를 재현한다.

```
solar index
vs
decay
```

### Level 2 — Density mediation

```
solar activity
→ MSIS density
→ decay
```

구조를 본다.

### Level 3 — Object sensitivity

```
altitude
mass
area
drag-related parameter
```

별 민감도 차이를 분석.

### Level 4 — Temporal robustness

```
different solar cycles
max/min periods
storm vs quiet
```

비교.

### Level 5 — Model validation

training에 사용하지 않은 시기/물체로 검증.

---

# 28. Dataset Construction

대상 물체 선정 기준을 사전에 정한다.

예:

```
LEO
sufficient observation span
sufficient GP/TLE density
low maneuver contamination
physical metadata availability
representative altitude groups
representative mass/area groups
```

그리고 exclusion criteria도 논문 전에 확정한다.

```
frequent maneuvers
poor identity
major metadata ambiguity
large observational gaps
reentry-specific unstable period
```

임의로 결과가 예쁜 물체만 골라서는 안 된다.

---

# 29. 연구 데이터 품질

각 object마다 QC report:

```
GP observation count
gap distribution
epoch coverage
altitude range
source conflicts
mass/area confidence
maneuver suspicion
reentry state
```

Space-weather도:

```
coverage
provisional/definitive
missing intervals
source
revision date
```

를 기록한다.

---

# 30. Decay Metric

`dh/dt`를 하나만 쓰지 말고 여러 정의를 sensitivity analysis에 사용한다.

예:

```
point-to-point
rolling linear slope
daily/weekly aggregated trend
long-window trend
```

각 방식의 noise sensitivity를 비교.

TLE/OMM이 precise osculating state vector가 아니라는 점을 Methods와 Limitations에서 분명히 적는다.

---

# 31. Statistical Design

논문 수준을 높이려면 최소한 다음 문제를 처리해야 한다.

```
autocorrelation
lag effects
multicollinearity
heteroskedasticity
unequal observation density
solar-cycle nonstationarity
object-level repeated measurements
```

가능한 분석:

```
correlation baseline
lagged correlation
multiple regression
robust regression
mixed-effects / hierarchical models
interaction terms
```

예:

```
density ~ F10.7 + Ap + altitude
decay ~ density + altitude + physical parameters
```

그리고:

```
density × altitude
density × A/m
```

같은 interaction을 보면 바로 연구 질문과 연결된다.

최종 모델은 데이터 진단 후 결정한다.

---

# 32. Validation

반드시 세 종류 검증을 한다.

### Temporal validation

한 기간으로 fit, 다른 solar-cycle period에서 test.

### Object holdout

일부 object는 모델 구축에서 제외하고 최종 검증에 사용.

### Method sensitivity

```
different smoothing windows
different decay estimators
observed vs adjusted F10.7
different geomagnetic indices
MSIS configuration
```

을 바꿔도 결론이 유지되는지 본다.

---

# 33. Figures

최종 논문 figure 후보:

```
research framework diagram
solar cycles + indices
sample object altitude histories
density vs solar activity
decay vs density
lag relationship
altitude-group sensitivity
physical-property sensitivity
model prediction vs observation
residual diagnostics
cross-cycle comparison
```

본문에는 핵심만, 나머지는 supplement.

---

# 34. Tables

최소:

```
object sample characteristics
data sources
variable definitions
model parameters
correlation/regression summary
sensitivity results
validation performance
```

를 준비한다.

---

# 35. Paper Structure

최종 manuscript:

```
Title

Abstract

1. Introduction
2. Background / Related Work
3. Data
4. Methods
5. Orbitoby-based reproducible pipeline
6. Results
7. Sensitivity Analysis
8. Validation
9. Discussion
10. Limitations
11. Conclusion

Data Availability
Software Availability
AI Usage Disclosure
Author Contributions
Acknowledgements
References
Supplement
```

Orbitoby 자체 설명은 Methods에서 필요한 만큼만.

논문의 주인공은 **연구 결과**다.

---

# 36. Reproducibility Package

논문이 끝날 때 다음 파일을 함께 고정한다.

```
analysis/
configs/
notebooks/
figures/
tables/
tests/

uv.lock
pyproject.toml

DATA_MANIFEST.json
PROVENANCE.json
CITATIONS.md
LICENSES.json
README_REPRODUCE.md
```

그리고 기록:

```
Orbitoby version
Orbitoby git commit
Orbitoby DOI
analysis git commit
retrieval dates
source dataset versions
model version
```

---

# 37. Software DOI

각 의미 있는 release마다 version DOI를 가질 수 있다.

연구 논문에는:

```
Orbitoby version used
+
exact version DOI
```

를 인용한다.

Zenodo는 software metadata에 `CITATION.cff`와 `.zenodo.json`을 지원한다. 둘 다 있으면 Zenodo는 `.zenodo.json`을 사용한다는 점도 현재 공식 문서에 명시돼 있다. [Zenodo](https://help.zenodo.org/docs/github/describe-software/?utm_source=chatgpt.com)

---

# 38. Research Paper Release

논문에서 사용한 순간에는:

```
Orbitoby vX.Y.Z-research
```

또는 정식 tag를 만든다.

그 release는 이후 기능이 변해도 절대 바뀌지 않는다.

논문 Methods에는:

```
software version
DOI
commit
```

을 모두 넣는다.

---

# 39. Software Paper

Orbitoby는 별도 software paper를 목표로 한다.

현재 JOSS는 단순 thin API client나 single-use utility가 아니라, **feature-complete, maintainably extensible, 연구적으로 의미 있고 실제/신뢰 가능한 연구 impact가 있는 software**를 요구한다. [joss.theoj.org](https://joss.theoj.org/about?utm_source=chatgpt.com)

이 때문에 우리가:

```
canonical model
identity
provenance
plugin system
time alignment
derived layer
license-aware export
```

까지 만드는 것이 중요하다.

Orbitoby는 그 정도까지 완성되면 단순 wrapper가 아니다.

---

# 40. JOSS 준비

현재 JOSS 정책상 비공개로 개발하다 공개한 프로젝트는 제출 전 최소 6개월의 공개 개발 이력이 필요하며 releases/issues/PRs 같은 공개 기록을 본다. [joss.theoj.org](https://joss.theoj.org/about?utm_source=chatgpt.com)

따라서 실제 public GitHub 시작이 2026년 9월 말이라면:

```
earliest realistic JOSS eligibility
≈ late March / April 2027
```

로 생각한다.

실제 repo 공개 시작일을 확인하고 다시 계산해야 한다.

---

# 41. JOSS 전에 반드시 만들 증거

```
real research using Orbitoby
versioned releases
public issues
public PR/history
tests
docs
architecture decisions
external install/use
citation
DOI
```

가 필요하다.

가능하면 외부 사용자 피드백 하나라도 받는다.

---

# 42. SoftwareX 대안

Orbitoby가 상세한 소프트웨어 설계와 실제 application을 설명하는 형태로 발전하면 SoftwareX도 후보가 될 수 있다. 현재 SoftwareX는 research software와 그 application을 다루는 peer-reviewed open-access 저널이다. [www.elsevier.com](https://www-prod.elsevier.com/researcher/author/tools-and-resources/research-elements-journals?utm_source=chatgpt.com)

다만 동일한 software paper를 여러 저널에 중복 제출하지 않는다.

최종 시점에:

```
JOSS
vs
SoftwareX
```

중 하나를 선택한다.

현재 Orbitoby의 성격에는 JOSS가 자연스럽지만, **실제 완성 상태를 보고 결정**한다.

---

# 43. 일정

## Phase A — 지금 ~ v0.1.0

**목표: 최대한 빠르게, 품질 gate 통과 시 release.**

```
repo audit
→ baseline tests
→ Master Plan lock
→ repository security
→ source framework
→ secure HTTP
→ credentials/plugins
→ canonical schema
→ identity
→ all planned sources
→ query APIs
→ derived
→ plot
→ export
→ docs
→ tests
→ PyPI
→ Zenodo DOI
```

가능하면 9월 말, 품질 문제면 아주 조금 미룬다.

---

# 44. 2026년 10월

목표:

> **Orbitoby로 연구 데이터셋을 실제로 만들 수 있는 달**

해야 할 것:

```
0.1.x stabilization
source health fixes
API ergonomics
performance
documentation

object selection
pilot dataset
quality-control rules
decay estimator validation
MSIS pipeline validation
baseline reproduction
```

10월 말에는 연구 데이터 구조를 더 이상 크게 바꾸지 않는다.

---

# 45. 2026년 11월

목표:

> **논문의 결과를 확정하는 달**

Orbitoby 개발 비중은 낮춘다.

```
full dataset
baseline analysis
density analysis
altitude sensitivity
physical sensitivity
solar-cycle comparison
lag analysis
validation
robustness
```

11월 말:

```
main numbers
main tables
main figures
```

가 거의 고정되어야 한다.

---

# 46. 2026년 12월

목표:

> **submission-ready research manuscript**

초반:

```
dataset freeze
analysis freeze
Orbitoby research release
DOI
```

중반:

```
Draft 1
internal review
method/statistics recheck
figure redesign
citation audit
```

후반:

```
Draft 2
reproduction test
language polish
final supplement
submission package
```

12월 말 목표는:

> **어디에 낼지만 정하면 바로 제출할 수 있는 manuscript.**

---

# 47. 2027년 1–2월

Orbitoby:

```
external user test
real-world bug fixes
API cleanup
docs polish
source stability
performance profiling
migration tests
```

Research:

```
paper submission/revisions
```

이 기간부터 `0.9.x`로 접근.

---

# 48. 2027년 3–4월

목표:

```
Orbitoby 1.0 release candidate
public history ≥ ~6 months
software-paper preparation
```

실제 public-history eligibility 확인 후 JOSS/SoftwareX 결정.

---

# 49. Orbitoby v1.0

이 시점의 Orbitoby는:

> **기능이 더 이상 추가될 게 없는 프로그램**이 아니라  
> **핵심 architecture/API에 대해 사용자에게 안정성을 약속할 수 있는 프로그램**

이어야 한다.

Release:

```
v1.0.0
PyPI
GitHub Release
Zenodo DOI
docs
CITATION
```

---

# 50. 최종 논문 두 개의 관계

가능하면 최종적으로:

### Paper A — Scientific paper

주제:

```
solar activity
thermospheric density
LEO orbital decay
altitude/object sensitivity
```

### Paper B — Software paper

주제:

```
Orbitoby architecture
provenance-first integration
multi-source identity
research workflows
extensibility
```

Paper A가 Orbitoby의 실제 research impact를 증명한다.

Paper B는 Orbitoby 자체에 학술적 credit을 준다.

굉장히 좋은 조합이다.

---

# 51. Weekly Operating Rhythm

네가 금요일에 시간이 상대적으로 많으니까 프로젝트 운영 자체도 고정해두자.

### 월–목

20~40분 수준.

```
small bug
test
paper reading
issue triage
documentation
analysis check
```

### 금요일

주요 deep-work.

```
3–5h+
main implementation
or
main analysis
```

마지막 20분:

```
tests
commit
issue/checklist update
next-Friday target
```

### 주말

필요하면:

```
paper reading
light review
figure checking
```

정도.

---

# 52. Scope-control Rule

앞으로 아이디어가 생기면 세 가지로 분류한다.

```
A. core correctness
→ 즉시

B. meaningful Orbitoby improvement
→ roadmap

C. interesting but orthogonal
→ backlog
```

새 기능 하나 때문에 기존 phase를 깨지 않는다.

---

# 53. Risk Register

|Risk|대응|
|---|---|
|API 변경|adapter isolation + contract/live test|
|source outage|cache + source health|
|source license 변경|policy review + metadata|
|secret leak|redaction + secret scanning|
|DB schema change|migration|
|plugin malicious code|explicit trust|
|package scope explosion|non-goals 고정|
|inconsistent physical metadata|assertion model|
|TLE/GP noise|multiple decay estimators|
|maneuver contamination|exclusion/QC|
|solar-index collinearity|diagnostics/model separation|
|temporal autocorrelation|time-series aware analysis|
|paper delayed by package work|Nov부터 연구 우선|
|AI-assisted development scrutiny|`AI_USAGE.md` + ADR + human verification|
|reproducibility failure|clean-machine reproduction test|

---

# 54. Final Audit

“끝났다”고 선언하기 전에 마지막으로 전수검사한다.

### Software

```
clean install
all tests
security
licenses
docs
API
plugins
migrations
built-ins
CLI
Colab
plot
exports
DOI
```

### Science

```
data QC
methods
statistics
figures
tables
references
limitations
reproducibility
```

### External reproduction

가능하면 제3자가 처음부터:

```
install
fetch
analyse
reproduce
```

해본다.

---

# 55. 최종 완료 상태

마지막 모습은 이거야.

```
Orbitoby
├── GitHub public repository
├── PyPI package
├── v1.0.0
├── Zenodo DOI
├── complete EN/KO documentation
├── stable APIs
├── vetted data sources
├── secure credentials/plugins
├── canonical research warehouse
├── provenance/reproducibility
├── quick plotting
├── derived science tools
├── CI/security/source health
└── software paper

2026 Science Day Research
├── complete dataset
├── reproducible analysis
├── frozen software version
├── figures/tables
├── full manuscript
├── software/data citations
├── DOI-linked software
└── scientific paper
```

그리고 이것까지 되면 단순히:

> “개인 프로젝트 하나 만들었다”

수준이 아니라,

> **공개 배포된 연구 소프트웨어를 직접 설계·개발하고, 실제 위성 궤도 연구에 적용하고, 그 연구 결과와 소프트웨어 자체를 각각 학술적으로 남긴 프로젝트**

가 된다.

나는 이 상태를 **Orbitoby의 진짜 최종 완료점**으로 잡는 게 가장 좋다고 본다.

그리고 한 가지를 특히 중요하게 생각해. **`v0.1.0`이 끝이라고 생각하지 않고, `v0.1.0 → 실제 연구 사용 → 검증/개선 → API freeze → v1.0 → software paper`가 하나의 연속된 프로젝트**여야 해. 그래야 Orbitoby가 단기 사이언스데이 도구가 아니라 네 전공에서 계속 가져갈 수 있는 제대로 된 연구 소프트웨어가 된다.