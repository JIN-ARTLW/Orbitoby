# Orbitoby: 통합 물리 제원 · TLE 결합 · Colab · PyPI 릴리스 후보

## 1. 실제 사용 가능한 데이터 범위

- 기본 모집단: `ob.catalog('all')`에서 반환되는 **전체 NORAD 목록**. 궤도 고도, 이심률, TLE 존재 조건을 적용하지 않는다.
- 기본적으로 `PAYLOAD` 위성만 선별하되 `satellites_only=False`로 모든 우주물체를 포함한다.
- 세 출처 중 **한 곳이라도 해당 정규화 물리량을 제공**하면 값이 있는 것으로 분류한다. 필요한 물리량이 여러 개인 경우 각 물리량은 서로 다른 출처가 제공해도 된다.
- 출처 이름 없이 `mass`, `area` 등을 조회한다. `include_sources=True`로 각 데이터의 원출처, 원본 필드, 모든 후보값을 별도 열로 추가한다. 출처 내역은 SQLite 원본에도 남는다.
- `mass_kg`: DISCOS 카탈로그 질량, GCAT 발사질량, KeepTrack 명시적 kg단위 보고 질량의 합집합. **각각 적용 시점이 같지 않을 수 있다.** 선택된 질량 유형은 `mass_definition`에 기록. 순서는 사용자 편의상 결정적 선택이며 정확도 순위가 아니다.
- `geometric_area_m2`: **DISCOS xSectAvg** 등 명시적 기하학적 면적. 본체 면적·레이더 반사단면적(RCS)·실제 항력 단면적과 다르다.
- `ballistic`: 실제 문서화한 탄도계수만. 현재 3종 수집기에 직접 탄도계수 제공 필드가 없다면 **후보 0개가 정상**이다. `m/(Cd*A_drag)`을 임의 `Cd`로 채우지 않는다. TLE `BSTAR`도 대신 쓰지 않는다.
- 5% 이상 값 불일치의 경우 `*_conflict=True`, 임의 평균 금지. 5% 이내라도 같은 값이 정확한 것으로 입증되는 것은 아니다. 원출처는 서로 의존할 수 있다.
- DISCOS 객체 수 2,200개는 **부분 수집 상태**. KEEPTRACK `brief`는 활성 카탈로그 일부 속성만 포함한다. API 호출 한도를 준수한다.

## 2. Mac 설치

```bash
cd ~/code/orbitoby
unzip -oq ~/Downloads/Orbitoby_Physics_TLE_Colab_Release_v2.zip -d ~/Downloads
bash ~/Downloads/Orbitoby_Physics_TLE_Colab_Release_v2/APPLY_TEST_MAC.command
```

## 3. 초급 문법 — 출처 통합

```python
import orbitoby as ob

result = ob.physical_satellites(required=["mass", "area"])
print(len(result.table), result.table.head())

# 이미 열린 DB에서 실행:
with ob.physics() as db:
    candidate = db.satellites(required=["mass", "area"])
    richer = db.satellites(required=["mass"], include_sources=True)
```

`result.table`은 pandas DataFrame이며 `result.manifest`는 모집단 크기·필수 조건·원본 수집 진행 상황·과학적 해석상 주의사항을 보존한다.

## 4. TLE 이력과 NORAD 기준 결합 — 데이터 누락 없이

```python
result = ob.physical_satellites(
    required=["mass", "area"],
    tle_parquet="~/Desktop/Orbitoby_TLE_History/data",
    include_sources=True,
)
result.to_csv("~/Desktop/Orbitoby_Physical_TLE_cohort.csv")
print(result.manifest["tle_join"])
```

이력 Parquet는 DuckDB를 사용하여 NORAD+epoch 열만 읽고 `COUNT(DISTINCT epoch)`, 최초·최종 관측시각을 계산한다. **TLE가 없어도 결과에서 위성을 삭제하지 않는다.** `has_tle_history=True`는 서로 다른 TLE 관측시각이 2개 이상이라는 뜻이지 궤도가 잘 관측되었다거나 탄도계수가 알려졌다는 뜻이 아니다. `tle_parquet` 옵션을 주지 않으면 TLE를 읽지 않아 물리량 필터만 수행한다.

## 5. CLI

```bash
cd ~/code/orbitoby
uv run --group dev python scripts/orbitoby_physical_cohort.py \
  --require mass --require area \
  --out ~/Desktop/Orbitoby_Physical_TLE_Research

uv run --group dev python scripts/orbitoby_physical_cohort.py \
  --require mass --require area --include-sources \
  --tle-parquet ~/Desktop/Orbitoby_TLE_History/data \
  --out ~/Desktop/Orbitoby_Physical_TLE_Research_WithHistory
```

추가 결과 `physical_satellites_manifest.json`을 CSV와 함께 연구 보존 자료로 저장한다. `--catalog-csv`로 원본 카탈로그 CSV를 지정해 Colab에서 비인증/오프라인으로 객체 목록을 사용 가능.

## 6. Colab

노트북: `notebooks/Orbitoby_Physical_TLE_Colab.ipynb`. PyPI 공개판에 이 모듈이 포함된 뒤 `pip install -U orbitoby`로 실행 가능. 공개 전에는 Git PR 브랜치의 소스 또는 빌드한 wheel을 별도로 설치해야 하며 현재 PyPI 0.1.1에는 이 API가 없다. **SQLite 물리 제원 캐시와 기본 카탈로그 CSV를 Drive에 복사하거나 Colab에서 정당한 범위만 재수집**해야 함. 토큰은 `getpass`, Colab Secrets 등 비노출 방식만 사용.

## 7. PyPI 배포 — 안전한 순서

1. 설치 스크립트에서 통합 테스트 통과, 실제 71,225 카탈로그·소규모 TLE 결합 실행.
2. `git status`, 파일 확인, PR 브랜치 커밋·푸시, 기존 **Python 3.12와 3.13 CI 실패 해결**.
3. `pyproject.toml`의 배포 버전을 이미 배포된 버전보다 새 번호로 **명시적으로** 설정. 기존 0.1.1을 덮어쓸 수 없음. 의존성/선택적 extras 검토.
4. `uv run --group dev python -m pytest -q`, `uv build`, wheel 설치 후 `ob.physical_satellites` import 검사, 필요하면 TestPyPI 사전 검증.
5. PyPI 프로젝트 설정에 Trusted Publisher (GitHub repo `JIN-ARTLW/Orbitoby`, workflow `publish-pypi.yml`, environment `pypi`) 등록. PR 병합 후 GitHub Actions 수동으로 승인하여 배포. 최소한 배포 워크플로에 부정확한 버전/비밀 키를 커밋하지 않아야 한다.
6. 공개 후 신규 Colab 런타임 Python 3.13 환경에서 실제 pip 설치와 샘플 조회 확인.

워크플로 템플릿은 `.github/workflows/publish-pypi.yml`이며 **설치 스크립트가 자동 설치하지 않는다**. 사용자가 리뷰하고 저장소에 복사해야 한다. 본 패치는 원격 GitHub와 PyPI에 접근하거나 게시한 상태가 아니다.

### 제공기관 이용 조건

GCAT과 DISCOS, KeepTrack의 데이터 접근/재배포 조건을 각각 준수. 특히 KeepTrack API 데이터는 CC BY-NC 4.0이며 자동화된 개별 상세 API 전수 스크레이핑은 금지. 이 패치는 수집된 로컬 DB에 대한 조회만 수행하고, 원본 데이터 파일을 Python wheel에 포함하지 않는다.
