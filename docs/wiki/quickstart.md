# 빠른 시작 / Quickstart

Orbitoby는 provider-native 원본과 provenance-rich canonical 연구 시계열을 분리합니다.  
Orbitoby separates provider-native data from provenance-rich canonical research series.

## 설치 / Install

```bash
python -m pip install orbitoby
```

NRLMSIS 2.1 계산이 필요할 때만 models extra를 설치합니다.

Install the models extra only when NRLMSIS 2.1 calculations are required.

```bash
python -m pip install "orbitoby[models]"
```

## Archive 열기 / Open an Archive

```python
from orbitoby import Archive

with Archive() as archive:
    print(archive.sources_available())
```

기본 archive 위치는 `~/.orbitoby`입니다. 다른 위치를 사용하려면 Orbitoby를 import하기 전에 `ORBITOBY_DATA_DIR` 환경변수를 설정합니다.

The default archive is `~/.orbitoby`. Set `ORBITOBY_DATA_DIR` before importing Orbitoby to use another location.

## 데이터 찾기 / Discover data

```python
with Archive() as archive:
    datasets = archive.datasets(metric="kp", live=False)
    for item in datasets:
        print(item["source"], item["dataset"])
```

`datasets()`는 curated catalogue를 검색합니다. `live=False`는 네트워크를 사용하지 않는 정적 탐색입니다. 실제 provider를 확인해야 할 때만 `live=True`를 명시합니다.

`datasets()` searches the curated catalogue. `live=False` is static and network-free. Use `live=True` only when provider-side discovery is intentionally required.

## Canonical 시계열 / Canonical time series

```python
with Archive() as archive:
    kp = archive.timeseries(
        "kp",
        source="gfz",
        dataset="kp",
        start="2024-05-10",
        end="2024-05-11",
    )

print(kp.head())
```

Canonical 조회 구간은 UTC `[start, end)`입니다. Orbitoby는 자동 interpolation, smoothing, resampling, `ffill`, `bfill`을 하지 않습니다.

Canonical query windows use UTC `[start, end)`. Orbitoby does not automatically interpolate, smooth, resample, forward-fill, or back-fill data.

## Provider-native 조회 / Provider-native fetch

```python
with Archive() as archive:
    raw = archive.fetch(
        source="swarm",
        dataset="density_a_pod",
        start="2024-05-10",
        end="2024-05-11",
    )

print(raw.columns)
```

`fetch()`는 provider 고유 필드를 그대로 다뤄야 할 때 사용합니다. 모든 native dataset이 canonical metric으로 매핑되는 것은 아닙니다.

Use `fetch()` when provider-specific fields are required. Native dataset availability does not imply a canonical mapping.

## 여러 시계열 exact 정렬 / Exact alignment

```python
with Archive() as archive:
    window = archive.window(
        fields=["kp", "ap"],
        source="gfz",
        start="2024-05-10",
        end="2024-05-11",
    )

print(window.data)
print(window.presence)
```

`ResearchWindow`는 실제 timestamp의 합집합에 exact 정렬합니다. 결측은 결측으로 유지됩니다.

`ResearchWindow` aligns on the union of actual timestamps. Missing data remains missing.

## 플롯 / Plot

```python
with Archive() as archive:
    kp = archive.timeseries(
        "kp",
        source="gfz",
        dataset="kp",
        start="2024-05-10",
        end="2024-05-11",
    )
    result = archive.plot(
        kp,
        kind="scatter",
        title="GFZ Kp",
    )
    result.save("kp.svg")
```

Orbitoby v0.1.1의 기본 plotting은 native SVG이며 별도 plotting framework를 요구하지 않습니다.

Orbitoby v0.1.1 uses a native SVG plotting path and does not require an external plotting framework.

## 다음 문서 / Next

- [데이터 탐색 / Discovery](discovery.md)
- [Provider 목록 / Providers](providers.md)
- [시계열 / Time series](timeseries.md)
- [Science Day 전체 예제 / Full Science Day workflow](science-day.md)
