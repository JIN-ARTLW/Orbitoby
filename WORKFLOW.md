# Orbitoby Science Day 연구 workflow

> Orbitoby core never guesses the data.
>
> 검증 기준: v0.1.0 Science Day 기능을 유지하는 v0.1.1 Colab compatibility release candidate. 2026-10-05 기준 local regression, minimum dependency, built-wheel, live provider workflow를 검증했으며 실제 PyPI v0.1.1은 공개 직후 새 Colab runtime에서 최종 확인합니다.

## 1. 준비

저장소: `~/code/orbitoby` · Python 3.12 이상 · MSIS 실행에는 `[models]` 필요.

### Google Colab

v0.1.1 공개 후 새 runtime에서 repository clone 없이 설치합니다.

```python
%pip install "orbitoby[models]==0.1.1"
```

Space-Track 인증정보는 Colab Secrets의 `SPACETRACK_USERNAME`, `SPACETRACK_PASSWORD`를 사용합니다. 전체 notebook은 `examples/science_day_colab.ipynb`입니다.

### Local development

```bash
cd ~/code/orbitoby
uv sync --group dev --extra models
```

Space-Track은 `SPACETRACK_USERNAME`, `SPACETRACK_PASSWORD`가 필요합니다. 선택적 DISCOS 조회에는 `ORBITOBY_DISCOS_TOKEN`이 필요합니다. 기존 환경변수 또는 명시적으로 허용한 저장소 `.env`를 사용하고 비밀값은 출력·공유하지 않습니다.

## 2. 현재 연결 확인

```bash
cd ~/code/orbitoby && .venv/bin/python scripts/check_connections.py --allow-dotenv
```

- `PASS`: 검사한 API/storage 또는 provider endpoint 응답 성공.
- `SKIP credential_not_configured`: 인증정보 미설정. 인증 성공을 뜻하지 않습니다.
- `FAIL`: 접근 거부, 네트워크 오류, 제한시간 초과 등을 구분해서 표시합니다.
- FAIL이 하나라도 있으면 exit 1, PASS/SKIP만 있으면 exit 0입니다.
- `.env`를 사용하지 않으면 `--allow-dotenv`를 생략합니다. 로컬 검사만 하려면 `--offline`, provider별 제한시간은 `--timeout 20`으로 지정합니다.

동일 DB의 writer 충돌을 피하도록 연결 진단과 workflow는 순차 실행합니다.

## 3. 실제 연구 실행 순서

| 단계 | 실제 API와 판단 기준 |
|---|---|
| 전체 population 확보 | `fetch(source="celestrak", dataset="satcat", all=True)`로 decayed 객체까지 포함한 SATCAT 보존 |
| 연구기간 존재 필터 | `objects(start=..., end=..., existence="throughout", object_type="payload")` |
| 비교할 위성 명시 | 예제는 Swarm A, NORAD 39452 선택. 전체 population의 대표 표본이라는 뜻은 아님 |
| Historical orbit | `orbit(norad_id=39452, start=..., end=...)`로 Space-Track GP_HISTORY 조회 |
| 궤도 조건 검사 | `orbit_summary(..., periapsis_km=(200, 2000), orbit_match="all", sync=False)` |
| 우주환경 조회 | GFZ observed F10.7/Kp/ap/daily Ap, Kyoto Dst, CDAWeb OMNI solar wind speed를 각각 명시적으로 조회 |
| 관측 기반 밀도 | Swarm `density_a_pod`의 `thermosphere_neutral_mass_density` 조회 |
| 모델 trajectory 구성 | 원 timestamp와 geodetic 좌표 사용. `Height_GD`의 m를 명시적으로 km로 변환 |
| MSIS forcing 구성 | `msis_inputs(..., driver_source="gfz", trajectory_parents=...)` |
| 모델 밀도 계산 | `msis_density(inputs, parents=parents)`로 NRLMSIS 2.1 실행 및 lineage 저장 |
| Exact 비교 | timestamp equality로 outer merge, `validate="one_to_one"`, 미일치 행 수 확인 |
| 연구 분석 | metadata completeness·quality flag·cohort를 검토한 뒤 항력/궤도 감소 분석을 별도로 수행 |

공개 시계열·window와 날짜 기반 orbit의 구간은 `[start, end)`입니다. population은 최신 SATCAT의 launch/decay 주장으로 과거 존재 조건을 평가하며 당시 catalogue 자체를 복원하지 않습니다.

## 4. 완성된 예제 실행

```bash
cd ~/code/orbitoby && .venv/bin/python examples/science_day.py --allow-dotenv
```

[전체 Python 예제](examples/science_day.py)는 UTC `2024-05-10`부터 `2024-05-11` 직전까지를 실행합니다. 각 단계 실패를 따로 보고하며 독립적인 다음 단계는 계속 진행합니다. FAIL/SKIP이 하나라도 있으면 exit 1입니다.

기본 출력:

```text
/tmp/orbitoby-science-day/
  report.json
  population.jsonl
  historical_orbit.jsonl
  f107_observed.jsonl
  kp.jsonl
  ap.jsonl
  ap_daily.jsonl
  dst.jsonl
  solar_wind_speed.jsonl
  density_comparison.jsonl
```

`--output 경로`로 출력 폴더를 지정할 수 있습니다. JSON Lines는 공유용 결과이며 원본 raw와 canonical/model 저장소도 함께 보존해야 재현할 수 있습니다. 기본 archive는 `~/.orbitoby`이고 다른 위치는 import 전 `ORBITOBY_DATA_DIR`로 지정합니다.

핵심 코드 — `archive`, `trajectory`, `trajectory_parents`, `observed` 구성은 전체 예제에 있습니다.

```python
inputs, parents = archive.msis_inputs(
    trajectory,
    driver_source="gfz",
    trajectory_parents=trajectory_parents,
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
assert comparison["_merge"].eq("both").all()
```

## 5. 과학적 처리 원칙

- 보간·스무딩·암묵적 resample·ffill·bfill·source 간 blending을 하지 않습니다.
- 여러 source가 가능하면 source/dataset을 명시합니다. `source_preference`는 장애 시 자동 fallback이 아닙니다.
- MSIS에는 이전 일 F10.7, 완전한 중심 81일 F10.7 평균, 정의된 Ap bin/vector가 필요합니다. 모델 정의 평균은 관측값 채움과 구분합니다.
- 필수 forcing 누락, 중복 유효 forcing, 중복 trajectory timestamp는 오류입니다. 중심 평균의 미래 정보 사용은 예측 연구에서 별도 검토합니다.
- Swarm은 `provider_derived`, MSIS는 `model_output`으로 구분합니다. 값뿐 아니라 source·artifact·quality·method·lineage를 보존합니다.
- Exact-time 일치와 결측 0개는 관측 품질·과학적 타당성의 인증이 아닙니다. 품질 flag와 비물리적 값은 명시적 QC로 검토합니다.
- Orbit 요약의 coverage는 실제 레코드가 있는 날짜 비율이며 연속 관측 coverage가 아닙니다.
- 같은 GP ID의 상충 내용은 오류로 거부합니다. 동일 내용 재수집만 idempotent하게 처리합니다.

## 6. 확인된 실행 결과

2026-10-04 실제 provider 조회 및 cache 재사용 실행:

| 항목 | 결과 |
|---|---|
| 기간 내 throughout payload | 13,142개 |
| 선택한 Swarm A historical orbit | 2 GP records, 1개 객체 screening PASS |
| F10.7 / Kp / ap / daily Ap | 1 / 8 / 8 / 1행 |
| Dst / solar wind speed | 24 / 24행 |
| Swarm POD / MSIS | 2,880 / 2,880행 |
| Exact-time 비교 | 2,880개 일치, 미일치 0 |
| observed/model missing flags | 0 / 0 |
| 전체 회귀 | 281 passed, Ruff·format·diff PASS |
| wheel/sdist·Twine·fresh base/models | PASS, 최대 3회 허용 중 1회 성공 |

당시 빠른 연결 진단에서는 CDAWeb capabilities가 20초 제한을 초과했지만 실제 OMNI 데이터 조회는 성공했습니다. DISCOS는 credential 미설정으로 SKIP이었습니다.

### v0.1.1 compatibility regression — 2026-10-05

| 항목 | 결과 |
|---|---|
| 최신 dependency 전체 회귀 | 284 passed |
| Colab baseline minimum dependency 전체 회귀 | 284 passed |
| built wheel 설치 | PASS |
| 기존 baseline dependency 강제 upgrade | 없음 |
| dependency consistency | PASS |
| MSIS extra (`pymsis==0.13.0`) | PASS |
| live population | 13,142 rows |
| historical orbit screening | PASS |
| F10.7 / Kp / ap / daily Ap | 1 / 8 / 8 / 1 rows |
| Dst / solar-wind speed | 24 / 24 rows |
| density exact comparison | 2,880 rows, mismatch 0 |
| observed/model missing | 0 / 0 |

CDAWeb quick capability probe는 timeout warning이 있었지만 실제 OMNI fetch는 성공했습니다. DISCOS는 credential 미설정으로 SKIP이었습니다. PyPI v0.1.1의 최종 Colab acceptance는 공개 직후 완전히 새로운 Colab runtime에서 수행합니다.


## 7. 남은 연구와 릴리스 경계

전체 population의 historical orbit bulk screening, 물리·임무 metadata completeness 평가, cohort/QC 결정, 항력·인과적 decay 분석은 별도 연구 작업입니다. 이 예제가 해당 분석까지 완료했다는 뜻은 아닙니다.

v0.1.0 Science Day 기능은 동결된 기준선으로 유지합니다. v0.1.0은 이미 PyPI에 공개되었으나 과도한 dependency minimum 때문에 Colab의 기존 pandas/requests 등을 불필요하게 교체하는 문제가 확인되었습니다. v0.1.1은 기능 확장이 아니라 이 설치 호환성 문제를 수정하고 동일 Science Day workflow를 Colab에서 재현 가능하게 만드는 patch release입니다.

- [한·영 위키](docs/wiki/index.md)
- [상세 workflow 검증 보고서](docs/RELEASE_0_1_0_REPORT.md)
- [빌드·설치 검증과 배포물 hash](dist/BUILD_REPORT.md)
- [연결 진단 코드](scripts/check_connections.py)
- [Colab 사용 가이드](docs/COLAB.md)
- [Colab Science Day notebook](examples/science_day_colab.ipynb)
