# 모델 / Models

`pip install "orbitoby[models]"`로 pymsis를 추가합니다. v0.1.1은 NRLMSIS 2.1 총 중성 질량밀도(`kg/m^3`)를 지원합니다.

Install pymsis with `pip install "orbitoby[models]"`. Version 0.1.1 supports NRLMSIS 2.1 total neutral mass density in `kg/m^3`.

`orbitoby.models.msis.calculate_msis_density(inputs)`에는 다음 열을 갖는 pandas DataFrame을 넘깁니다.

Pass a pandas DataFrame with these columns to `orbitoby.models.msis.calculate_msis_density(inputs)`:


| 열 / Columns | 의미 / Meaning |
| --- | --- |
| `timestamp`, `longitude_deg`, `latitude_deg`, `altitude_km` | UTC 시각·경도·위도·고도 / UTC time, longitude, latitude, altitude |
| `f107_previous_day_sfu` | 이전 날 F10.7 / Previous-day F10.7 |
| `f107a_81day_centered_sfu` | 중심 81일 평균 / Centered 81-day mean |
| `ap_daily`, `ap_current_3h` | 일 Ap·현재 3시간 ap / Daily Ap and current three-hour ap |
| `ap_3h_prior`, `ap_6h_prior`, `ap_9h_prior` | 3·6·9시간 이전 / Three, six, and nine hours earlier |
| `ap_12_33h_avg`, `ap_36_57h_avg` | 12–33·36–57시간 이전 평균 / Means over 12–33 and 36–57 hours earlier |

입력 시각·좌표·지수는 의도한 계산 조건에 과학적으로 맞아야 합니다. 직접 calculate 경로는 지수를 추정·자동 다운로드하지 않으며 `interpolate_indices=False`입니다. 중심 평균의 미래 자료 사용 가능성은 예측 연구에서 별도로 검토합니다.

Times, coordinates, and forcing must scientifically match the intended evaluation. The direct calculate path does not infer or auto-download indices and sets `interpolate_indices=False`. Predictive studies must separately consider future information in a centered mean.

기본 `geomagnetic_activity=-1`은 storm-time Ap, 명시적 `1`은 daily Ap입니다. 두 모드 모두 요구 열을 공급해야 합니다. 반환 `MSISRun`은 결과·모델/백엔드 버전·입력 문맥을 포함하며 관측 밀도가 아닙니다.

The default `geomagnetic_activity=-1` uses storm-time Ap; explicit `1` selects daily Ap. Supply all required columns in either mode. `MSISRun` includes results, model/backend versions, and input context; it is not an observed density.

영속 저장에는 `archive.msis_density(inputs, parents=...)`를 사용합니다. `orbitoby.warehouse.products.ProductParent`로 실제 입력 출처를 연결하며 `f107_previous_day_input`, `f107a_81day_input`, `ap_input` 역할이 필요합니다. 통과만을 위해 lineage ID를 만들어내지 않습니다.

Persist with `archive.msis_density(inputs, parents=...)`. Use `orbitoby.warehouse.products.ProductParent` to reference actual inputs with roles `f107_previous_day_input`, `f107a_81day_input`, and `ap_input`. Never invent lineage identifiers merely to pass validation.


## Archive forcing 구성 / Archive forcing construction

```python
inputs, parents = archive.msis_inputs(
    trajectory, driver_source="gfz", trajectory_parents=trajectory_parents
)
modeled = archive.msis_density(inputs, parents=parents)
lineage = archive.product_store.lineage(modeled.iloc[0]["product_id"])
```

`trajectory`는 timestamp/longitude_deg/latitude_deg/altitude_km입니다. `trajectory_parents`는 실제 artifact를 참조하는 ProductParent 목록입니다. `driver_source="gfz"`를 필수로 명시하며 이 경로는 GFZ F10.7/일 Ap/3시간 ap를 cache 또는 네트워크로 조회합니다. 저수준 `build_msis_inputs(trajectory, f107=..., ap_daily=..., ap_3h=...)`는 주어진 canonical 표만 사용합니다.

Supply the four trajectory columns and real ProductParent references. Explicit driver_source='gfz' retrieves daily F10.7, daily Ap and three-hour ap through cache/network. The low-level build_msis_inputs uses only supplied canonical frames.

이전 UTC 일 F10.7, 중심 ±40일 총 81일 F10.7, 현재 UTC 3시간 bin 및 3/6/9시간 전 ap, 12–33/36–57시간 각 8개 bin 평균을 구성합니다. floor는 지수의 정의된 interval 선택이며 nearest matching이 아닙니다. 필수 day/bin 누락, 중복 유효 forcing, 중복 trajectory timestamp는 실패합니다. 소스 간 fallback·보간·채움은 없습니다.

The transform constructs previous-day F10.7, a complete centered ±40-day mean, the current and prior 3/6/9-hour ap bins, and the two eight-bin Ap means. Flooring selects defined intervals, not nearest observations. Missing required days/bins, duplicate valid forcing and duplicate trajectory timestamps fail. No cross-source fallback or filling occurs.

모델 output은 input context와 backend/model 버전, forcing policy 및 lineage를 저장합니다. 입력 출처의 과학적 적합성은 사용자가 검토해야 하며 parent ID의 존재 확인만으로 값의 진실성을 인증하지 않습니다. 항력·SGP4 전파·인과적 decay 추정은 이 API에 포함되지 않습니다.

Outputs retain input context, backend/model versions, forcing policy and lineage. Existing parent IDs do not independently certify scientific correctness. Drag, SGP4 propagation and causal decay estimation are outside this API.
