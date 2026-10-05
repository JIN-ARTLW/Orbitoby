# Science Day 실행 예제 / Research workflow

[examples/science_day.py](https://github.com/JIN-ARTLW/Orbitoby/blob/main/examples/science_day.py)는 날짜 2024-05-10 UTC 하루를 시연합니다. 39452(Swarm A)는 명시적으로 선택한 예제이며 통계적으로 대표적인 cohort가 아닙니다.

The example demonstrates one UTC day, 2024-05-10. NORAD 39452 (Swarm A) is explicitly selected for demonstration, not a statistically representative cohort.

```bash
.venv/bin/python examples/science_day.py --allow-dotenv
```

전체 SATCAT → 기간 throughout payload → Swarm A historical orbit 및 LEO 범위 screening → GFZ F10.7/Kp/ap/Ap → Kyoto Dst → CDAWeb OMNI solar wind → Swarm POD → 명시적 GFZ forcing → NRLMSIS 2.1 → one-to-one exact merge 순서입니다. source별 실패를 독립 보고하며 다른 검증 가능한 단계를 계속합니다. 하나라도 FAIL/SKIP이면 exit 1입니다.

Stages are complete SATCAT, period payloads, selected historical orbit/LEO screening, GFZ indices, Kyoto Dst, CDAWeb OMNI wind, Swarm POD, explicit forcing, MSIS and validated exact merging. Failures are reported separately while independent stages continue; any FAIL/SKIP exits 1.

출력은 기본 `/tmp/orbitoby-science-day/`의 단계별 JSON Lines와 report.json입니다. JSON은 공유용 예시 export이며 canonical/product Parquet와 raw가 재현성 원본입니다. 위성 전체를 GP_HISTORY로 bulk 조회하지 않으며 물리/임무 metadata completeness 평가·QC·cohort·항력/감쇠 분석은 연구자가 추가해야 합니다. DISCOS는 token을 설정해 fetch할 수 있으나 예제가 불완전한 mass를 채우지는 않습니다.

Stage JSON Lines and report.json default to /tmp/orbitoby-science-day/. JSON is a sharing example; raw and canonical/product archives remain the reproduction source. The script does not request GP_HISTORY for all satellites or decide metadata completeness, QC, cohorts, drag or decay. DISCOS metadata can be fetched with a token; missing mass is not fabricated.

[실행 증거 / Execution evidence](https://github.com/JIN-ARTLW/Orbitoby/blob/main/docs/RELEASE_0_1_1_REPORT.md) · [모델 / Models](models.md) · [제약 / Limitations](limitations.md)


## Colab에서 실행 / Run in Colab

저장소 clone 없이 PyPI 설치만으로 실행할 수 있습니다.

The Colab workflow runs from the published package without cloning the repository.

```python
%pip install -U "orbitoby[models]"
```

기본 검증 기간은 다음과 같습니다.

```python
START = "2024-05-10"
END = "2024-05-11"
NORAD_ID = 39452
```

일반적으로 연구기간을 바꿀 때는 `START`, `END`만 변경합니다. 구간 의미는 UTC `[start, end)`입니다.

For ordinary reuse, change `START` and `END`. The interval is UTC `[start, end)`.

Space-Track historical orbit을 사용하려면 Colab Secrets에 `SPACETRACK_USERNAME`, `SPACETRACK_PASSWORD`를 등록합니다. secret 값 자체는 출력하지 않습니다.

The public notebook is available at [examples/science_day_colab.ipynb](https://github.com/JIN-ARTLW/Orbitoby/blob/main/examples/science_day_colab.ipynb).

## End-to-end 단계 / End-to-end stages

```text
CelesTrak complete SATCAT
        ↓
period payload population
        ↓
researcher-selected Swarm A / NORAD 39452
        ↓
Space-Track historical GP
        ↓
orbital-envelope screening
        ↓
GFZ F10.7 / Kp / ap / daily Ap
        ↓
WDC Kyoto Dst
        ↓
CDAWeb OMNI solar-wind speed
        ↓
Swarm POD canonical density
        +
Swarm source-native trajectory
        ↓
GFZ MSIS forcing construction
        ↓
NRLMSIS 2.1 model_output
        ↓
exact one-to-one timestamp merge
```

## Swarm trajectory

Swarm canonical density frame와 source-native frame은 분리해서 사용합니다.

```python
observed = archive.timeseries(
    "thermosphere_neutral_mass_density",
    source="swarm",
    dataset="density_a_pod",
    start=START,
    end=END,
)

native = archive.fetch(
    source="swarm",
    dataset="density_a_pod",
    start=START,
    end=END,
)
```

MSIS trajectory schema는 다음 네 field입니다.

```python
trajectory = pd.DataFrame(
    {
        "timestamp": pd.to_datetime(native["Timestamp"], utc=True),
        "latitude_deg": native["Latitude_GD"],
        "longitude_deg": native["Longitude_GD"],
        "altitude_km": native["Height_GD"] / 1000.0,
    }
)
```

## MSIS와 exact comparison

```python
inputs, parents = archive.msis_inputs(
    trajectory,
    driver_source="gfz",
    trajectory_parents=trajectory_parents,
)

modeled = archive.msis_density(
    inputs,
    parents=parents,
)

comparison = observed.merge(
    modeled,
    on="timestamp",
    how="outer",
    suffixes=("_observed", "_model"),
    validate="one_to_one",
    indicator=True,
)

assert comparison["_merge"].eq("both").all()
```

이 exact merge는 timestamp 정합성 검증이지 관측 품질이나 모델 정확성 인증이 아닙니다.

Exact matching validates timestamp correspondence; it does not certify observational quality or model accuracy.

## v0.1.1 검증 기준 / Validated reference

2024-05-10 하루 smoke에서 확인된 값은 다음과 같습니다.

| Output | Rows |
|---|---:|
| period payload population | 13,142 |
| F10.7 | 1 |
| Kp | 8 |
| ap | 8 |
| daily Ap | 1 |
| Dst | 24 |
| solar-wind speed | 24 |
| Swarm observed density | 2,880 |
| MSIS modeled density | 2,880 |
| exact timestamp matches | 2,880 |
| timestamp mismatches | 0 |

이 숫자는 해당 하루의 release smoke reference입니다. 날짜를 바꾸면 row count는 달라질 수 있으므로 일반적인 hard requirement가 아닙니다.

These counts are release-smoke references for that specific day, not universal row-count requirements.

## 연구자가 별도로 결정할 것 / Researcher decisions

Orbitoby가 자동으로 결정하지 않는 항목:

- scientific variables
- study period
- orbital envelope
- historical coverage threshold
- satellite cohort
- mission, mass, shape, inclination and manoeuvre context
- QC policy
- orbital-decay methodology
- statistical interpretation

Software workflow success and scientific validity are separate claims.
