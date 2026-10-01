# Orbitoby

**Orbitoby** is a local-first Python package for acquiring, preserving, integrating, querying, and managing non-image space and aerospace research data.

**Orbitoby**는 위성·우주물체·우주환경·태양활동·발사·임무 등 비이미지 우주·항공우주 연구 데이터를 수집, 보존, 통합, 조회하고 재현 가능하게 관리하기 위한 local-first Python 패키지입니다.

> **Status:** Public development / pre-release  
> **상태:** 공개 개발 중 / v0.1.0 개발 단계

Orbitoby is currently under active public development toward its first substantial public release, **v0.1.0**.

The repository already contains a functional prototype, but not every API or data-management feature described in the roadmap has been implemented yet.

Orbitoby는 현재 첫 본격 공개 릴리스인 **v0.1.0**을 개발하고 있습니다.

현재 저장소에는 실제 동작하는 프로토타입이 포함되어 있지만, 로드맵에 정의된 모든 API와 데이터 관리 기능이 구현된 상태는 아닙니다.

---

## Why Orbitoby? / 왜 Orbitoby인가?

Space and aerospace research data are distributed across many providers, archives, formats, authentication systems, time resolutions, update schedules, and licensing conditions.

Orbitoby aims to provide a unified research-oriented data lifecycle:

```text
discover
→ acquire
→ preserve
→ validate
→ normalize
→ integrate
→ query / derive
→ export / reproduce
```

우주·항공우주 연구 데이터는 여러 기관과 아카이브에 분산되어 있고, 데이터 형식, 인증 방식, 시간 해상도, 갱신 주기, 라이선스 조건도 서로 다릅니다.

Orbitoby는 이러한 데이터를 하나의 연구 데이터 생애주기로 연결하는 것을 목표로 합니다.

---

## Core principles / 핵심 원칙

### Local-first

User research data remains on the user's own machine by default.

사용자의 연구 데이터는 기본적으로 사용자 자신의 컴퓨터에 저장됩니다.

Orbitoby does not require a central database server operated by the maintainer.

Orbitoby 개발자가 중앙 데이터베이스 서버를 운영하는 구조가 아닙니다.

### Raw-first preservation

Original provider responses are preserved whenever legally and technically appropriate, together with checksums and provenance metadata.

가능한 경우 제공처의 원본 응답을 checksum 및 출처 정보와 함께 보존합니다.

### File-first research storage

Raw files and columnar research data are primary research artifacts.

대용량 연구 데이터는 파일 중심으로 관리하며, Parquet / Arrow와 같은 columnar 형식을 활용하는 방향으로 설계합니다.

### Minimal embedded metadata engine

DuckDB may be used internally for lightweight metadata, identity, coverage, and query support.

DuckDB는 사용자 로컬 환경에서 metadata, identity, coverage, 검색 보조 등을 위해 제한적으로 사용하는 embedded engine입니다.

It is an implementation detail, not a hosted Orbitoby database service.

### Provenance-first

Conflicting claims from different providers are preserved rather than silently overwritten.

서로 다른 제공처가 같은 객체에 대해 다른 값을 제공하는 경우 하나를 임의로 덮어쓰지 않고 각 출처의 주장을 보존합니다.

### Explicit scientific transformations

Observed/provider data and modelled/derived data must remain distinguishable.

관측 또는 제공 데이터와 모델·파생 데이터는 명확히 구분합니다.

### Extensible source architecture

Orbitoby is designed to support:

- built-in vetted sources
- persistent user-defined sources
- declarative HTTP sources
- trusted third-party Python plugins

Orbitoby는 기본 제공처뿐 아니라 사용자 정의 source와 외부 plugin으로 확장 가능한 구조를 목표로 합니다.

---

## Current prototype / 현재 프로토타입

The current development version includes foundations for:

- immutable raw-response archiving
- SHA-256 artifact tracking
- local coverage and cache tracking
- historical orbital-element storage
- conservative NORAD / COSPAR identity handling
- provenance-preserving source records
- multiple source adapters

현재 개발 버전에는 다음 기능의 기반 구현이 포함되어 있습니다.

- 불변 원본 응답 아카이브
- SHA-256 artifact 추적
- 로컬 coverage / cache 관리
- 과거 궤도요소 저장
- 보수적인 NORAD / COSPAR 객체 식별
- 출처가 보존되는 source record
- 다중 데이터 제공처 adapter

### Existing source adapters / 현재 포함된 adapter

- CelesTrak
- GCAT
- Launch Library 2
- NOAA SWPC
- SatNOGS
- Space-Track

Adapter availability does **not** mean that every dataset from that provider has completed Orbitoby's stable-source admission process.

Adapter가 존재한다고 해서 해당 제공처의 모든 데이터셋이 Orbitoby의 최종 stable-source 검증을 완료했다는 뜻은 아닙니다.

---

## Target v0.1.0 / v0.1.0 목표

Orbitoby v0.1.0 is intended to be the first substantial general-purpose research-data release, rather than a reduced package built only for a single Science Day project.

v0.1.0은 특정 Science Day 연구에 맞춘 축소판이 아니라, Orbitoby의 첫 범용 연구 데이터 관리 릴리스를 목표로 합니다.

Major targets include:

- hardened source / dataset metadata and policy model
- secure HTTP handling
- rate limiting, retries, caching and credential management
- immutable raw archive and reproducible normalization
- scalable ingestion for large catalogues and time series
- file-first research storage
- lightweight embedded metadata and query support
- canonical space and aerospace data domains
- conservative cross-source identity resolution
- persistent user-defined sources
- declarative HTTP sources
- trusted Python plugin discovery
- high-level research APIs
- explicit time-series alignment
- provenance, citation and license reporting
- CSV and Parquet export
- Jupyter and Colab workflows
- orbital derived quantities
- MSIS-based modelled thermospheric density
- orbital-decay and drag-related transforms
- lightweight scientific `.plot()` quick-look support
- bilingual English / Korean public documentation
- automated tests, CI and security checks
- PyPI publication
- Zenodo version DOI

Detailed planning documents:

- `docs/ORBITOBY_MASTER_PLAN.md`
- `docs/ORBITOBY_ARCHITECTURE_V0.1.0.md`
- `docs/ORBITOBY_V0.1.0_CHECKLIST.md`

---

## Architecture / 아키텍처

The approved storage direction is:

```text
External space / aerospace archives
                ↓
        Source + Dataset adapters
                ↓
    Acquire / Validate / Normalize
                ↓
┌────────────────────────────────────┐
│       User-local Orbitoby data     │
│                                    │
│  Raw files + manifests             │
│  Parquet / Arrow research data     │
│  Minimal embedded DuckDB metadata  │
└────────────────────────────────────┘
                ↓
      Identity / Query / Derived
                ↓
     Python API / CLI / Notebook
                ↓
  Export + Provenance + Citation
```

Orbitoby remains a Python package.

The embedded database is local to each user's installation and does not require the maintainer to operate a central database server.

Orbitoby는 Python 패키지이며, 내부 DuckDB는 각 사용자 환경에 종속되는 로컬 데이터 관리 수단입니다.

---

## Intended API / 목표 API

The public API is still evolving toward v0.1.0.

```python
from orbitoby import Archive

archive = Archive()

obj = archive.object(norad_id=25544)

orbit = archive.orbit(
    norad_id=25544,
    start="2025-01-01",
    end="2025-03-01",
)

weather = archive.space_weather(
    start="2025-01-01",
    end="2025-03-01",
    fields=["f107", "kp", "ap"],
)

window = archive.window(
    norad_id=25544,
    start="2025-01-01",
    end="2025-03-01",
    include=["orbit", "physical", "space_weather"],
)

series = archive.timeseries(
    norad_id=25544,
    start="2025-01-01",
    end="2025-03-01",
    fields=[
        "orbit.altitude_km",
        "space_weather.f107",
    ],
)

series.plot()
```

Some APIs shown above are target v0.1.0 APIs and may not yet be implemented in the current development snapshot.

위 예시 중 일부는 v0.1.0 목표 API이며, 현재 개발 버전에서 아직 구현되지 않았을 수 있습니다.

---

## Installation / 설치

Orbitoby has not yet reached its first PyPI release.

Orbitoby는 아직 첫 PyPI 정식 릴리스 전입니다.

### Development installation

```bash
git clone https://github.com/JIN-ARTLW/Orbitoby.git
cd Orbitoby
uv sync
```

After the first release, the intended installation method is:

```bash
pip install orbitoby
```

---

## Public development / 공개 개발

Orbitoby is developed publicly on GitHub.

Major architecture and scientific decisions are reviewed and approved by the human maintainer.

AI tools may assist with:

- implementation
- repetitive refactoring
- documentation
- test generation
- debugging
- research workflow design

AI-generated work is not treated as completed until it has been reviewed and validated.

Orbitoby의 핵심 아키텍처와 연구적 판단은 사람이 검토·승인합니다.

AI는 구현과 반복 작업을 보조하지만, 실제 검토와 테스트를 통과하기 전에는 완료된 작업으로 간주하지 않습니다.

See:

- `CONTRIBUTING.md`
- `AI_USAGE.md`

---

## Scientific development / 연구 활용

Orbitoby is being developed alongside a reproducible research application investigating relationships among solar activity, thermospheric density, and low-Earth-orbit orbital decay.

That study is an application and validation case for Orbitoby.

Orbitoby itself is designed as a broader general-purpose space and aerospace research-data package.

Orbitoby는 태양활동–열권밀도–저궤도 궤도감쇠 연구와 함께 개발되고 있지만, 해당 연구는 첫 활용 및 검증 사례이며 패키지의 전체 사용 범위를 제한하지 않습니다.

---

## Licensing / 라이선스

Orbitoby source code is licensed under the **Apache License 2.0**.

Third-party datasets retain their original:

- copyright
- licenses
- attribution requirements
- terms of use
- redistribution restrictions

Orbitoby 소스 코드는 **Apache License 2.0**으로 배포됩니다.

외부 데이터셋의 권리와 이용 조건은 각 원 제공처의 조건을 따릅니다.

The Toby mascot, photographs, and original brand artwork are not licensed under Apache-2.0 unless explicitly stated otherwise.

---

## Security / 보안

Do not commit:

- provider passwords
- API keys
- tokens
- `.env` files
- private archives
- user research data

See `SECURITY.md`.

---

## Author / 저자

**Jin Yeseo (진예서)**

GitHub: `JIN-ARTLW`  
Email: `jinyeseo.public@gmail.com`

---

## Citation

Formal citation metadata and a Zenodo DOI will be added with the first public software release.

정식 `CITATION.cff`와 Orbitoby Zenodo DOI는 첫 공개 릴리스와 함께 추가될 예정입니다.

---

## Project status

**Current:** active public development  
**Next milestone:** Orbitoby v0.1.0  
**Distribution target:** PyPI  
**Archival target:** Zenodo DOI
