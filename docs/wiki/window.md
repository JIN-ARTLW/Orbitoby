# ResearchWindow와 exact 정렬 / ResearchWindow and exact alignment

```python
with Archive() as archive:
    window = archive.window(
        fields=["kp", "ap"], source="gfz", start="2024-05-10", end="2024-05-11"
    )
    print(window.data, window.presence, window.missing_reason)
    values = window.to_numpy()
```

관측 timestamp의 합집합에 equality로 정렬합니다. 일평균 지수가 00:00에 있다는 이유로 하루 전체에 복제하지 않습니다. timestamp/metric 중복과 여러 단위는 오류입니다. 기본 `artifact_resolution="all"`; 사용자가 명시적으로 선택한 `preferred`는 우선순위 선택이며 충돌의 과학적 해결이 아닙니다.

Alignment uses timestamp equality on the union of observations. A daily index at midnight is not repeated across the day. Duplicate metric/timestamp claims and mixed units raise errors. Explicit `preferred` is priority selection, not scientific conflict resolution.

`data`: 값 표, `presence`: 원 행 존재 여부, `missing_reason`: provider 결측 사유, `provenance`: 원 long-form 표, `units`: 단위 dict, `metrics`: 물리량 순서. `to_numpy()`는 값 행렬이며 단위/출처를 함께 넘기지 않습니다. `presence=True`여도 provider fill로 value가 결측일 수 있습니다. absent observation은 presence=False로 구분합니다.

The object contains values, original-row presence, provider missing reasons, long-form provenance, unit mapping and metric order. `to_numpy()` returns values without carrying units/provenance. Present rows may still contain provider fill values; absent observations have presence=False.

`window()`에 `alignment`, `cadence`, `norad_id` 인자는 없습니다. 관측/model은 동일 metric이므로 한 pivot에 몰아넣지 말고 별도 표를 exact merge하며 one-to-one 검증과 미일치 개수를 확인하세요.

There are no alignment, cadence or norad_id arguments. Observed/model density share a metric name; compare separate frames with a validated exact merge and count unmatched timestamps.


## 반환 객체 읽기 / Reading a ResearchWindow

```python
window = archive.window(
    fields=["kp", "ap"],
    source="gfz",
    start="2024-05-10",
    end="2024-05-11",
)

print(window.metrics)
print(window.units)
print(window.data.head())
print(window.presence.head())
print(window.missing_reason.head())
```

- `data`: exact-aligned value table
- `presence`: 해당 timestamp/metric 원 행 존재 여부
- `missing_reason`: provider가 표현한 결측 사유
- `provenance`: 정렬 이전 long-form provenance
- `units`: metric별 단위
- `metrics`: metric 순서

`to_numpy()`는 값 행렬만 반환하므로 단위와 provenance를 별도로 유지해야 합니다.

`to_numpy()` returns only the value matrix; keep units and provenance alongside it when reproducibility matters.
