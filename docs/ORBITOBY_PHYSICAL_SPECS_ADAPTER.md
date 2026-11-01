# Orbitoby: Physical Specification Evidence Adapter (2026-11-01)

## 목적 및 연구적 주의

**추가 모듈** `orbitoby.physical_specs`는 두 데이터원을 NORAD ID로 결합합니다.

- **GCAT**: 질량(발사 시점), 건조질량, 본체 길이·직경, 구조물 포함 최대 span, 형상, 추정값 표시. 원본 출처: Jonathan McDowell, [GCAT 문서](https://planet4589.org/space/gcat/web/cat/cols.html). TSV 원본: `https://planet4589.org/space/gcat/tsv/cat/satcat.tsv`, `.../satcat100k.tsv`.
- **ESA DISCOS**: 인증된 API v2에서 질량·형상·기하학적 단면적 `xSectAvg / xSectMin / xSectMax`를 **선택적인 소수 NORAD ID**에 대해 조회. 계정/토큰 필요. [DISCOS](https://discosweb.esoc.esa.int/).
- **임무 기술문서 수동 증거 CSV**: 태양전지판 상태, 전체 외부 표면적, 자세 조건에 따른 투영 단면적과 각 출처 URL을 직접 검토한 후 입력. 예제 템플릿 `manual_evidence_template.csv`는 빈 헤더만 제공하며 어떠한 물리량도 만들어 넣지 않습니다.

**핵심 구분**: GCAT 본체 치수로 자세 의존적인 항력 단면적을 **확정할 수 없습니다**. GCAT `span`도 태양전지판이 반드시 있다는 뜻이 아닙니다. DISCOS의 `xSectAvg`는 카탈로그의 기하학적 단면적이며 현재 자세의 항력 투영면적이나 항력계수 `Cd`가 아닙니다. GCAT의 `MassFlag == '?'`는 추정값이라는 표시이며, 건조질량과 발사 질량은 폭풍 당시 질량을 보장하지 않습니다.

## 설치 (Mac / Linux / Windows Python)

```bash
unzip -q Orbitoby_Physical_Specs_Patch.zip -d /tmp/orbitoby_phys_patch
python3 /tmp/orbitoby_phys_patch/orbitoby_physical_specs_patch/install_patch.py ~/code/orbitoby
cd ~/code/orbitoby
uv run --group dev pytest -q tests/test_physical_specs.py
```

`install_patch.py`는 기존 파일을 덮어쓰지 않고, 프로젝트 패키지 구조를 감지하여 모듈·스크립트·테스트·README를 복사합니다. **자동 커밋/푸시하지 않습니다.**

## GCAT 전체 물리제원 수집·필터

```bash
cd ~/code/orbitoby
uv run --group dev python scripts/orbitoby_build_physical_specs.py \
  --out ~/Desktop/Orbitoby_PhysicalSpecs \
  --tier catalog_physical_partial
```

일반적으로 `physical_specs_all.csv`, `physical_specs_selected.csv`, `physical_specs_manifest.json`, `source_cache/`가 생성됩니다. 기본 선택은 **payload** 중 발사 질량·본체 길이·직경이 있는 객체만입니다. GCAT 원본은 캐시 후 재사용하고 사용·재배포 조건은 제공처 지침을 확인해야 합니다. `--refresh-gcat`을 지정해야 재다운로드합니다.

## strict_documented: 엄격한 '출처 존재' 조건

1. `docs/physical_specs_manual_evidence_template.csv`를 복제하고 논문·공식 위성 기술문서에서 **개별 NORAD ID 기준**으로 확인한 항목만 작성합니다.
2. 태양전지판 상태(`present`, `absent`, `unknown`), 해당 근거 URL, **전체 외부 표면적과 근거 URL**, **자세 조건에서의 투영 단면적과 근거 URL**, `attitude_context`를 모두 기입합니다.
3. 실행:

```bash
uv run --group dev python scripts/orbitoby_build_physical_specs.py \
  --out ~/Desktop/Orbitoby_PhysicalSpecs_Validated \
  --manual-evidence ~/Desktop/checked_satellite_specs.csv \
  --tier strict_documented \
  --orbit-csv ~/Desktop/OrbitobyPlots_v02/orbitoby_satellite_records.csv
```

`strict_documented`는 **각 필드가 양수이고 출처 URL을 기록했는지 확인하는 증거 완결성 필터**입니다. URL이 정말 내용을 뒷받침하는지, 수치 정확도가 어떤지 자동 검증하는 기능은 없습니다. 사람이 검토해야 합니다. 근거 없는 값은 엄격 조건에서 제외되며 0개가 나올 수 있습니다.

## ESA DISCOS 선택 연결 (토큰 비공개)

공식 API 가입 후 환경변수를 사용자 PC에서 지정하고 대상 소수 ID만 명시합니다.

```bash
export ORBITOBY_DISCOS_TOKEN='여기에_본인의_실제_API_토큰'
uv run --group dev python scripts/orbitoby_build_physical_specs.py \
  --out ~/Desktop/Orbitoby_PhysicalSpecs_DISCOS \
  --discos-ids 35693,35694 \
  --tier all
unset ORBITOBY_DISCOS_TOKEN
```

모듈은 **30개 NORAD ID 이하/실행**으로 제한하고 토큰은 파일에 남기지 않습니다. ESA의 계정/API/출처표기·재배포 조건을 따라야 합니다. 이 패치는 미인증 상태에서 실제 API 응답을 테스트하지 않았습니다.

## 출력 파일 및 기록

- `physical_specs_all.csv`: GCAT 메타데이터 + 선택적 ESA + 수동 증거; 누락값은 누락으로 유지
- `physical_specs_selected.csv`: `--tier` 및 기본 payload 조건을 통과한 객체
- `orbit_physical_joined.csv`: `--orbit-csv` 제공 시 NORAD ID 기반 연결 결과
- `physical_specs_manifest.json`: 원본 URL, SHA256, 캐시 경로, 처리 시점 및 결측 경고
- `source_cache/*.tsv`: 원본 GCAT 다운로드 (저장소에 올리지 마세요)

코드의 질량 단위는 kg, 크기 m, 면적 m²입니다. GUI QuickPlot v0.3과 연결하려면 이 출력 CSV를 추가 데이터 레이어로 이용하면 됩니다. **이번 패치는 GUI EXE 자체를 변경하지 않습니다.**

## Git 수동 반영

```bash
cd ~/code/orbitoby
uv run --group dev pytest -q tests/test_physical_specs.py
git status --short
git add src/orbitoby/physical_specs.py scripts/orbitoby_build_physical_specs.py tests/test_physical_specs.py docs/physical_specs_manual_evidence_template.csv docs/ORBITOBY_PHYSICAL_SPECS_ADAPTER.md
git commit -m "feat: add provenance-aware satellite physical specs adapters"
git push
```

**주의**: 로컬 패키지가 `orbitoby/` 루트 구조라면 위 `git add src/...` 대신 `git add orbitoby/physical_specs.py`를 사용해야 합니다. 기존 연구용 브랜치·CI·테스트를 확인하고 푸시하세요. API 토큰·대량 원본 TSV·연도별 TLE 파일을 저장소에 추가하지 마세요.

## 검증 상황

- 2026-11-01: 구조·오프라인 파서/필터/결합 테스트 통과.
- 이 실행 환경에는 사용자 Mac의 저장소, 전체 Parquet, ESA 인증정보가 없어 **실제 GCAT 전체 다운로드, DISCOS API 응답, 사용자 저장소 통합 테스트 및 git push는 미완료**.
