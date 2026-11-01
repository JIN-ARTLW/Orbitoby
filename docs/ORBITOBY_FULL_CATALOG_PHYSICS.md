# Orbitoby: 전체 NORAD 카탈로그 물리 제원 전수 선별 v2

## 이번 버전에서 바뀐 부분

이전 `orbitoby_join_all_physical_specs.py`는 `satellite_monthly_le550.csv`를 모집단으로 사용해서 **고도·TLE 이력 필터를 통과한 19,540개**만 대조했습니다.

새 `scripts/orbitoby_full_catalog_physics.py`는 `orbitoby.catalog('all', refresh=False)`를 **모집단**으로 사용합니다. **궤도 고도, 발사 시점, 분석 날짜, TLE 이력 길이, CubeSat 여부를 일절 제한하지 않습니다.** 전체 인공우주물체를 보존한 `all_catalog_norad_physical_evidence.csv`에서 **PAYLOAD에 해당하는 인공위성만** `all_satellite_payloads.csv`로 별도 분류합니다. 분류 불명도 별도 CSV로 남깁니다. 68개의 TLE Parquet 자료는 이번 작업에 필요하지 않습니다.

## 설치

이번 패치는 이전에 설치한 `src/orbitoby/physical_specs.py`를 **수정하지 않습니다.**

Mac 다운로드 폴더에 ZIP을 저장한 뒤:

```bash
unzip -oq ~/Downloads/Orbitoby_PhysicalSpecs_FullCatalog_v2.zip -d ~/Downloads
bash ~/Downloads/Orbitoby_PhysicalSpecs_FullCatalog_v2/APPLY_TEST_MAC.command
```

기존 파일을 덮어쓰지 않고 새 스크립트·테스트·설명서를 설치합니다. 설치 스크립트는 **Git 커밋/푸시를 자동으로 수행하지 않습니다.**

## 전체 카탈로그 조사 실행 (DISCOS 토큰 없이)

```bash
cd ~/code/orbitoby
uv run --group dev python scripts/orbitoby_full_catalog_physics.py \
  --out ~/Desktop/Orbitoby_PhysicalSpecs_All_Catalog
```

`orbitoby.catalog('all')`에 접근할 수 없는 경우, 예전에 저장한 **전체 카탈로그** CSV를 명시합니다(550km 플롯 CSV를 사용하면 안 됨):

```bash
uv run --group dev python scripts/orbitoby_full_catalog_physics.py \
  --catalog-csv ~/Desktop/Orbitoby_All_Satellites_TEST_NoDst/data/ALL_catalog_NORAD_objects.csv \
  --out ~/Desktop/Orbitoby_PhysicalSpecs_All_Catalog
```

원본 출처 기록과 SHA256은 `full_catalog_physical_manifest.json`에 저장됩니다. `--gcat-dir`에 기존 캐시 폴더를 지정하면 GCAT 재다운로드를 피할 수 있습니다.

## ESA DISCOS 자료 연결 (토큰 없는 방식)

계정 및 이용 권한 확보 후 **합법적으로 추출한 CSV 파일**이 있는 경우 `--discos-csv /path/to/authorized_export.csv`를 추가합니다. CSV 필드는 `norad_id,discos_mass_kg,discos_xsect_avg_m2,discos_xsect_min_m2,discos_xsect_max_m2,discos_shape,discos_source_url` 중 ID와 실제 제공된 필드입니다. API 호출이나 토큰은 **이 스크립트에서 하지 않습니다**. ESA 이용 제한과 출처 표시 준수 필요.

DISCOS의 `xSectAvg` 등은 **카탈로그상 기하학적 단면적**이며 운용 중의 항력 투영 단면적 `A_drag`와 동일하다고 간주하지 않습니다. 따라서 `catalog_m_a_geometry_proxy_kg_m2`는 `m/A_geom` 참고 비율일 뿐 **탄도계수 B가 아닙니다.**

## 임무 기술문서의 고신뢰 제원 연결

`docs/physical_evidence_template.csv`의 컬럼에 NORAD ID별 검증 자료를 추가하고 `--manual-evidence` 인자를 사용합니다.

- `mass_kg`, `drag_projected_area_m2`, `drag_coefficient` 각 값에 **각각 출처 URL** 필요
- 세 값의 임무 시점·자세 조건을 공유하는 `configuration_context_id`와 확인 가능한 `attitude_context`가 있어야 계산
- **`B = m / (C_D * A_drag)` [kg/m²]**, 역계수 `C_D * A_drag / m` [m²/kg]
- 논문이 직접 제시한 B는 `published_ballistic_coefficient_kg_m2` / `bc_source_url` 별도 사용
- GCAT의 `Mass`는 발사 시점 질량이며, 추정 표시 `?`가 없어도 완전한 직접측정/운용질량을 보장하지 않습니다.
- 본체 직경·형상이 `Sphere` 등으로 명시된 경우에 한해 **구형 본체 기하학 참조 면적**은 계산하지만, 실제 `A_drag`로 승격하지 않습니다.
- TLE의 BSTAR는 B가 아닙니다.

## 출력 파일

| 파일 | 설명 |
| --- | --- |
| `all_catalog_norad_physical_evidence.csv` | 전체 NORAD 객체. GCAT/DISCOS 미대응도 보존 |
| `all_satellite_payloads.csv` | PAYLOAD로 분류된 전체 위성. 궤도 조건 없음 |
| `satellites_mass_and_dimensions.csv` | GCAT 질량과 본체 길이·직경 모두 있는 후보 |
| `satellites_mass_plus_catalog_geometric_area.csv` | 질량 + DISCOS 기하학적 단면적이 있는 후보 (실제 항력면적과 다름) |
| `satellites_documented_ballistic_coefficient.csv` | 문헌상 B 또는 독립 검증값으로 B 계산 가능한 후보 |
| `satellites_need_drag_area_or_cd.csv` | 질량 기록은 있으나 B를 확정할 자료가 부족한 후보 |
| `unresolved_object_class_or_gcat.csv` | 위성 여부 미분류 / GCAT 미연결 또는 충돌 |
| `physical_coverage_report.csv` | 필드별 확보 건수 및 위성 모집단 대비 비율 |
| `full_catalog_physical_manifest.json` | 실제 객체 수·입력 데이터 출처·제한·SHA256 |

**주의:** 엄격 탄도계수 후보가 0개로 나오는 것은 토큰 미설정이나 코드 오류를 뜻하지 않습니다. 현재 연결 자료에 `m`, `A_drag`, `C_D` 또는 출처 명시된 B가 없다는 뜻입니다. 결과 수는 실제 실행 뒤에만 확정할 수 있습니다.

## 테스트 및 GitHub

설치 실행 파일에서 신규 테스트를 돌립니다. 앞선 PR은 main 직접 push가 금지되고 일부 Python 회귀 테스트가 실패했습니다. 따라서 자동 push하지 않습니다.

로컬 변경 사항을 확인한 후 기존 PR 브랜치에서 테스트·커밋·푸시하세요.

```bash
cd ~/code/orbitoby
git status --short
uv run --group dev python -m pytest -q tests/test_full_catalog_physics.py tests/test_physical_specs.py
# CI 회귀 실패 로그는 별도 확인 필요
git add scripts/orbitoby_full_catalog_physics.py tests/test_full_catalog_physics.py docs/physical_evidence_template.csv docs/ORBITOBY_FULL_CATALOG_PHYSICS.md
git commit -m 'feat: screen full NORAD catalog for documented physical properties'
git push -u origin feat/physical-specs-adapter
```

출처: [GCAT](https://planet4589.org/space/gcat/), [GCAT 컬럼 설명](https://planet4589.org/space/gcat/web/cat/cols.html), [ESA DISCOS](https://discosweb.esoc.esa.int/).
