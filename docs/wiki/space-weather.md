# 우주환경 시계열 / Space-weather series

`Archive.space_weather()`는 지원되는 canonical space-weather metric을 provenance와 함께 조회합니다.

`Archive.space_weather()` queries supported canonical space-weather metrics with provenance.

```python
from orbitoby import Archive

with Archive() as archive:
    weather = archive.space_weather(
        start="2024-05-10",
        end="2024-05-11",
        fields=["kp", "ap"],
        source="gfz",
    )

print(weather.head())
```

## 시간 의미 / Time semantics

Canonical 조회는 UTC `[start, end)`를 사용합니다.

Canonical queries use UTC `[start, end)`.

```text
start <= timestamp < end
```

Orbitoby는 데이터가 없다고 해서 자동으로 값을 생성하지 않습니다.

Orbitoby does not manufacture values when data is unavailable.

- no interpolation
- no smoothing
- no implicit resampling
- no `ffill`
- no `bfill`
- no silent source blending

## v0.1.1 Science Day에서 검증된 series / Series validated in the v0.1.1 Science Day workflow

| Metric | Source | Dataset/notes |
|---|---|---|
| `f107_observed` | `gfz` | observed F10.7 |
| `kp` | `gfz` | 3-hour Kp |
| `ap` | `gfz` | 3-hour ap |
| `ap_daily` | `gfz` | daily Ap |
| `dst` | `wdc_kyoto` | hourly Dst |
| `solar_wind_speed` | `cdaweb` | `omni_hourly` |

```python
with Archive() as archive:
    f107 = archive.space_weather(
        start="2024-05-10",
        end="2024-05-11",
        fields="f107_observed",
        source="gfz",
    )

    dst = archive.space_weather(
        start="2024-05-10",
        end="2024-05-11",
        fields="dst",
        source="wdc_kyoto",
    )

    wind = archive.space_weather(
        start="2024-05-10",
        end="2024-05-11",
        fields="solar_wind_speed",
        source="cdaweb",
        dataset="omni_hourly",
    )
```

## Source 선택 / Source selection

여러 source가 같은 metric을 제공하면 source를 명시하는 것이 가장 재현성이 높습니다.

When several sources can provide the same metric, explicitly selecting the source is the most reproducible approach.

```python
kp = archive.space_weather(
    start="2024-05-10",
    end="2024-05-11",
    fields="kp",
    source="gfz",
)
```

`source_preference`는 첫 matching binding을 선택하는 우선순위 정책이며 runtime 장애 시 자동 fallback이 아닙니다.

`source_preference` is an ordered binding-selection policy, not automatic runtime outage fallback.

## Artifact resolution

기본 `artifact_resolution="all"`은 서로 다른 artifact의 중복 주장을 보존합니다.

The default `artifact_resolution="all"` preserves duplicate claims from different artifacts.

명시적으로 `preferred` 정책을 사용할 수 있지만 이는 과학적 충돌 해결 자체가 아닙니다.

An explicit preferred-resolution policy may be used, but it is not scientific conflict adjudication.

## 연구자가 확인할 것 / Researcher responsibilities

- provider revision / revision policy
- quality flags
- sampling cadence
- missingness
- dataset citation
- provider licensing and redistribution terms
- 모델 forcing에 사용할 때 미래 정보 사용 여부

특히 MSIS의 centered 81-day F10.7 mean은 정의상 미래 정보를 포함하므로 예측 연구에서는 별도로 판단해야 합니다.

In particular, the centered 81-day F10.7 mean used by the MSIS forcing path contains future information by definition and must be considered separately in forecasting studies.
