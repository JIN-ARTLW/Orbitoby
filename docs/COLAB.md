# Orbitoby on Google Colab

## v0.1.1 목표

Orbitoby v0.1.1은 v0.1.0에서 확립한 Science Day workflow를 Google Colab에서 repository clone 없이 실행할 수 있도록 하는 compatibility patch release입니다.

Colab 사용자는 PyPI에서 Orbitoby를 설치한 뒤 공개 API만으로 population, historical orbit, space-weather, Swarm density, MSIS density workflow를 실행할 수 있어야 합니다.

## 설치

v0.1.1 공개 후 새 Google Colab runtime에서 실행합니다.

```python
%pip install "orbitoby[models]==0.1.1"
```

Orbitoby 설치는 이미 호환되는 Colab 기본 dependency를 불필요하게 upgrade하지 않아야 합니다.

검증 baseline:

```text
Python        3.13
numpy         2.1.3
duckdb        1.3.2
pandas        2.2.3
pyarrow       23.0.1
python-dotenv 1.2.3
pytz          2025.2
requests      2.32.4
pymsis        0.13.0
```

Python 3.12에서도 전체 regression suite를 별도로 검증합니다.

## 인증정보

Historical orbit 조회에는 Space-Track 계정이 필요합니다. Colab Secrets에 다음 이름으로 저장합니다.

```text
SPACETRACK_USERNAME
SPACETRACK_PASSWORD
```

선택적 DISCOS 기능에는 `ORBITOBY_DISCOS_TOKEN`을 사용할 수 있습니다.

인증정보 값 자체는 notebook 출력이나 공유 파일에 포함하지 않습니다.

## Science Day workflow

Colab workflow는 다음 경로를 검증합니다.

```text
CelesTrak SATCAT population
    ↓
연구기간 existence filtering
    ↓
payload filtering
    ↓
historical Space-Track orbit
    ↓
orbital-envelope screening
    ↓
GFZ F10.7 / Kp / ap / daily Ap
    ↓
WDC Kyoto Dst
    ↓
CDAWeb OMNI solar-wind speed
    ↓
Swarm POD neutral-density series
    ↓
MSIS forcing construction
    ↓
NRLMSIS 2.1 model density
    ↓
exact timestamp comparison
```

## 과학적 처리 원칙

Orbitoby는 연구자의 데이터 선택을 추측하지 않습니다.

- source와 dataset을 명시적으로 선택합니다.
- 자동 interpolation, smoothing, implicit resampling, ffill, bfill을 하지 않습니다.
- 서로 다른 source의 값을 암묵적으로 blending하지 않습니다.
- Swarm density는 provider-derived observation으로 구분합니다.
- MSIS density는 model output으로 구분합니다.
- provenance와 lineage를 보존합니다.
- exact timestamp match와 missing=0은 과학적 타당성 자체를 의미하지 않습니다.

## v0.1.1 검증 결과

2026-10-05 local release candidate:

```text
latest dependency regression       284 passed
minimum dependency regression      284 passed
built-wheel install                PASS
dependency forced upgrade          NONE
dependency consistency             PASS
Science Day API                    PASS
MSIS extra                         PASS
```

실제 provider workflow:

```text
population                         13,142 rows
historical orbit screening         PASS
F10.7                              1 row
Kp                                 8 rows
ap                                 8 rows
daily Ap                           1 row
Dst                                24 rows
solar-wind speed                   24 rows
density comparison                 2,880 rows
exact timestamp mismatch           0
observed missing                   0
model missing                      0
```

CDAWeb quick capability probe는 제한시간을 초과할 수 있지만 동일 검증에서 실제 OMNI solar-wind 조회는 성공했습니다. DISCOS는 credential이 설정되지 않은 경우 정상적으로 SKIP할 수 있습니다.

## 최종 PyPI / Colab acceptance

v0.1.1 공개 후 반드시 완전히 새로운 Colab runtime에서 다시 확인합니다.

1. `%pip install "orbitoby[models]==0.1.1"` 성공
2. Colab의 기존 compatible dependency가 불필요하게 변경되지 않음
3. `orbitoby.__version__ == "0.1.1"`
4. Space-Track credentials를 Colab Secrets에서 사용 가능
5. repository clone 없이 Science Day notebook 실행 가능
6. population / historical orbit / space weather 조회 성공
7. Swarm density 조회 성공
8. MSIS model density 생성 성공
9. exact timestamp comparison 성공
10. provenance와 model/observation 구분 유지

## 연구 범위와 별도 작업

위 workflow는 데이터 획득 및 비교 파이프라인의 검증입니다. 실제 Science Day 연구에서는 연구기간, 사용할 태양·지자기 변수, orbital envelope, historical orbit coverage 기준, 위성 cohort, mission 특성, 질량·형상, inclination, manoeuvre 가능성, QC 기준, orbital-decay 분석 방법을 별도로 결정합니다.
