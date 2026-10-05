# Orbitoby v0.1.1

**Orbitoby core never guesses the data.**

Orbitoby는 우주환경·위성 궤도 연구를 위한 provenance-first Python toolkit입니다. provider-native 자료, canonical 시계열, 우주물체 catalogue, historical orbit, exact-time 정렬, Swarm 밀도와 명시적 NRLMSIS 계산을 하나의 재현 가능한 연구 흐름으로 연결합니다.

Orbitoby is a provenance-first Python toolkit for space-weather and orbital research. It connects provider-native data, canonical scientific time series, object catalogues, historical orbit, exact-time alignment, Swarm density, and explicit NRLMSIS evaluation in a reproducible workflow.

## 설치 / Install

```bash
pip install orbitoby
```

MSIS 모델 기능이 필요하면:

```bash
pip install "orbitoby[models]"
```

## 처음이라면 / Start here

- 데이터를 먼저 찾고 싶다 → [Discovery](discovery.md)
- 처음부터 한 번 써보고 싶다 → [Quickstart](quickstart.md)
- 전체 연구 흐름을 보고 싶다 → [Science Day workflow](science-day.md)
- 지원 provider를 확인하고 싶다 → [Providers](providers.md)
- 전체 public API를 보고 싶다 → [API inventory](api-inventory.md)

## 핵심 원칙 / Core principles

- Canonical query interval은 UTC `[start, end)`입니다.
- 자동 interpolation, smoothing, resampling, `ffill`, `bfill`을 하지 않습니다.
- provider-native 자료와 canonical 자료를 구분합니다.
- observation/provider-derived 자료와 `model_output`을 구분합니다.
- 여러 source가 있을 때 하나를 암묵적으로 과학적 진실로 판정하지 않습니다.
- exact timestamp 일치는 QC 또는 과학적 타당성 인증이 아닙니다.
- provenance와 lineage는 결과의 일부로 취급합니다.

Canonical queries use UTC `[start, end)`. Orbitoby does not silently interpolate, smooth, resample, fill, blend providers, or treat a successful software run as proof of scientific validity.

## 기본 데이터 흐름 / Basic data flow

```text
Provider
   |
   +-- fetch() -------- provider-native data
   |
   +-- canonical binding
           |
           v
      timeseries()
           |
           +-- value / unit
           +-- missingness
           +-- source / dataset
           +-- artifact_id
           +-- provenance
                |
                v
             window()
        exact-time alignment
```

위성 연구에서는 catalogue와 historical orbit 흐름을 별도로 연결할 수 있습니다.

```text
CelesTrak SATCAT
       |
       v
    objects()
       |
       v
researcher selection
       |
       v
     orbit()
       |
       v
 orbit_summary()
```

## 문서 / Documentation

| 목적 / Goal | 문서 / Page |
|---|---|
| 설치 | [Installation](installation.md) |
| 첫 사용 | [Quickstart](quickstart.md) |
| 데이터 탐색 | [Discovery](discovery.md) |
| 전체 provider | [Providers](providers.md) |
| 우주물체 | [Catalogue](catalogue.md) |
| 기간 population | [Population](population.md) |
| 과거 궤도 | [Historical orbit](orbit.md) |
| 우주환경 | [Space weather](space-weather.md) |
| 시계열 | [Time series](timeseries.md) |
| exact alignment | [ResearchWindow](window.md) |
| 플롯 | [Plotting](plotting.md) |
| Swarm | [Swarm](swarm.md) |
| NRLMSIS | [Models](models.md) |
| 저장·provenance | [Storage](storage.md) |
| 확장 | [Sources & plugins](extensions.md) |
| 문제 해결 | [Troubleshooting](troubleshooting.md) |
| 전체 API | [API inventory](api-inventory.md) |

## 현재 공개 버전 / Current release

현재 공개 버전은 **v0.1.1**입니다.

v0.1.1 is the current public alpha release.

[Release & versioning →](release.md)
