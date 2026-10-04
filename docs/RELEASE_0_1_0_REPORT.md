# v0.1.0 연구 workflow 재검증 / Research workflow verification

2026-10-04, 사용자 로컬 checkout `~/code/orbitoby`. 이 보고서는 이전 2026-10-03 release 후보 기록을 대체합니다. 수정 전 문서는 `/tmp/orbitoby-before-review-20261004/`에 보존했습니다. 기존 uncommitted/untracked 작업은 유지했고 reset/revert, commit/tag, push, PyPI upload는 수행하지 않았습니다.

This report supersedes the previous candidate record. Pre-edit documents were preserved in the temporary backup. Existing user changes remain; no reset/revert, commit/tag, push or PyPI upload was performed.

## 코드와 원칙 / Code and principles

초기 `tests/` 전체는 263 passed였습니다. 현재 구현·테스트에서 canonical 결측/단위/원값, exact window와 duplicate 오류, raw/canonical/product 저장 및 lineage, population/역사 궤도 경계, 모델 forcing 정의를 확인했습니다.

The baseline tests/ suite passed 263 tests. Review covered canonical missingness/units/original values, exact windows, duplicate rejection, archive/product lineage, population/orbit bounds and model forcing.

확인한 결함을 최소 수정했습니다.

Minimal corrections address demonstrated issues:

- `msis_inputs()`의 내부 preferred 선택을 all로 변경해 중복 유효 driver를 거부합니다. / Preserve all forcing claims and reject duplicate valid values.
- 모든 driver 행에 raw artifact ID를 요구합니다. / Require raw provenance for every driver row.
- 동일 GP ID의 다른 내용은 명시적 오류로 거부하고 같은 내용만 idempotent 처리합니다. / Reject conflicting GP content; identical repeats remain idempotent.

provider QC 자동 적용, 결측 metadata 추정, source 간 blending, resample/보간/채움은 추가하지 않았습니다. 명시적 모델 정의 평균과 최신 SATCAT projection의 의미는 위키에 설명합니다. parent 존재 검증은 값의 과학적 진실성을 인증하는 장치가 아닙니다.

No automatic QC, guessed metadata, cross-source blending or filling was added. Model-defined means and latest-snapshot semantics are documented. Parent existence is not scientific certification.

## 실제 E2E / Actual E2E

`examples/science_day.py --allow-dotenv`, UTC `[2024-05-10, 2024-05-11)`. 첫 실행에서 공유용 Parquet export가 빈 context struct를 저장하지 못했습니다. core 조회/cache는 성공했고 예제 export를 JSON Lines로 수정한 재실행은 exit 0입니다. 실제 provider 수집 후 재실행에서 cache를 재사용했습니다.

The first run exposed an example-only Parquet export failure on empty context structs. Core acquisition/cache worked. The corrected JSON Lines example returned exit 0, reusing cached data after actual provider acquisition.

| 단계 / Stage | 결과 / Result |
|---|---|
| 전체 SATCAT → throughout payload | PASS, 13,142 selected objects |
| Swarm A / NORAD 39452 historical orbit | PASS, 2 GP records; 1-object orbit_summary screening |
| GFZ observed F10.7 | PASS, 1 row |
| GFZ Kp / ap / daily Ap | PASS, 8 / 8 / 1 rows |
| Kyoto hourly Dst | PASS, 24 rows |
| CDAWeb OMNI solar wind speed | PASS, 24 rows |
| Swarm A POD | PASS, 2,880 rows |
| explicit GFZ forcing → NRLMSIS 2.1 | PASS, 2,880 model rows |
| outer exact one-to-one comparison | PASS, 2,880 matches, no unmatched timestamps |
| observed/model missing flags | 0 / 0; not a substitute for scientific QC |

실행 JSON 보고서와 단계별 자료는 `/tmp/orbitoby-science-day/`에 있습니다. 원본·canonical·모델은 현재 archive에 보존합니다. default archive에는 이전 2,880행 run이 없어 새로 수집했습니다. 다른 임시 archive를 병합하지 않았습니다.

Stage output is in the temporary example directory; raw, canonical and model products remain in the current archive. The default archive lacked the previous 2,880-row run, so data was acquired again. Separate temporary archives were not merged.

전체 population의 historical orbit을 bulk screening한 것이 아닙니다. 명시적 예제 Swarm A만 조회했습니다. DISCOS token은 미설정이며 물리/임무 metadata 완전성, cohort 선정, quality flag 해석, 항력/decay 분석은 연구 단계로 남습니다.

This is not bulk historical-orbit screening of the whole population. Swarm A was an explicit demonstration choice. DISCOS is unconfigured; physical/mission completeness, cohort/QC decisions and drag/decay analysis remain research work.

## 연결 진단 / Connection diagnostic

```bash
.venv/bin/python scripts/check_connections.py --allow-dotenv
```

15 registered sources와 핵심 API·local DB/storage PASS. CelesTrak/GFZ/NRCan/Kyoto/Swarm/NOAA/Space-Track PASS. DISCOS는 credential 미설정 SKIP. CDAWeb capabilities probe는 기본 20초 deadline 초과 FAIL로 exit 1입니다. 실제 OMNI data query 성공과 짧은 connectivity deadline 실패를 혼동하지 않습니다. 최초 병렬 실행의 DB lock 실패는 workflow 종료 후 순차 재검사에서 해소되었습니다.

Registry, API/storage and seven provider probes passed. DISCOS skipped missing credentials. CDAWeb capabilities exceeded the default 20-second worker deadline, causing exit 1 despite the successful actual OMNI query. An initial concurrent-writer DB check failure disappeared when diagnostics ran sequentially after the workflow.

## 문서와 동결 / Documentation and freeze

README 한·영 재작성, docs/wiki의 20개 주제+index, 실제 signature와 전체 103 curated datasets inventory를 작성했습니다. 기존 짧은 guides는 최신 위키로 연결합니다. 기존 master plan의 orbit end-inclusive 설명을 현재 half-open으로 수정했습니다. source 수와 dataset 수는 등록 상태이며 모든 경로의 live 안정성 보증이 아닙니다.

README and the wiki cover 20 topics plus an index, exact API signatures and 103 curated datasets. Old guide paths link to current pages. Stale orbit interval claims were corrected. Registry counts do not certify universal live availability.

변경 파일 범위: README.md, pyproject.toml, src/orbitoby/service.py, examples/science_day.py, scripts/check_connections.py, tests/test_msis_forcing.py, tests/test_connection_check.py, tests/test_orbit_conflicts.py, docs/wiki/*.md, docs/index.md, docs/{installation,quickstart,catalogue,timeseries,plotting,models,plugins,architecture,provenance,licensing,release}.md, docs/ORBITOBY_MASTER_PLAN.md, 이 보고서와 freeze ADR.

The list above identifies this pass's edits; it does not attribute pre-existing user changes to this work.

## 전체 회귀 / Full regression

- `git diff --check`: PASS.
- `ruff check --no-cache .`: PASS.
- `ruff format --check --no-cache .`: PASS, 134 files formatted at code freeze.
- Full pytest, plugin autoload disabled, warnings=error, Python -X dev -B, no cacheprovider: **276 passed in 7.76s**.
- tests/ baseline 263 + new regression cases; full discovery also includes seven existing local handoff tests. / tests/ 기준 증가분 외 전체 discovery는 기존 handoff 7개도 포함합니다.
- Local README/wiki links: no broken targets. / 로컬 링크 오류 없음.

## 빌드와 남은 게이트 / Build and remaining gates

코드·문서는 이 지점에서 동결합니다. post-build 증거·정확한 wheel/sdist hash와 fresh base/models 결과는 **dist/BUILD_REPORT.md**에 별도로 기록합니다. 이 보고서는 빌드 입력이므로 자신의 배포물 hash를 포함하지 않습니다. 최대 3회 허용, 성공한 첫 회에서 종료합니다.

Source/docs are frozen here. Post-build evidence, hashes and fresh-install results are recorded separately in dist/BUILD_REPORT.md so this build input does not contain a self-referential hash. At most three attempts are allowed, stopping on first success.

공개 전 남은 게이트: 기존 사용자 변경과 untracked 구현을 포함한 release commit/tag 확정, 공개 저장소 문서 링크 확인, 실제 게시 결정. 이 작업은 PyPI 업로드를 수행하지 않습니다. CDAWeb 짧은 진단 timeout과 DISCOS 미설정은 명시적 환경/연결 제약으로 남습니다.

Before publication: review and fix the release commit/tag including existing untracked implementation, verify hosted documentation links and decide publication. This task performs no PyPI upload. The short CDAWeb timeout and missing DISCOS credential remain explicit connectivity/environment limits.
