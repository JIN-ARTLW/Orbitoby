# Orbitoby v0.1.0 — 개발·출시 체크리스트 / Development & Release Checklist

문서 버전: 1.3 · 갱신일: 2026-09-28 (KST) · 상태: 전체 범위 유지, 9월 30일 PyPI·공개 DOI 완료 역산 계획 확정; G0~G4 미통과

최신 일정: [9월 28·29·30일 출시 실행 계획](ORBITOBY_SEPTEMBER_RELEASE_PLAN.md). 사용자 최신 지시에 따라 기존 10~20시간 제한을 일정 입력에서 제외하고 9월 30일 정식 PyPI·동일 릴리스 공개 DOI 완료에서 역산한다. Codex는 설계·코드·테스트·절차를 제공하고 사용자가 적용·실행·수정·검증한다. v1.0으로 발전 가능한 구조를 우선하며 기능·품질은 축소하지 않는다. [출시 준비 재점검](ORBITOBY_V0.1.0_READINESS_REVIEW.md)의 기술적 발견은 유효하고 과거 시간 제약·일정 평가는 당시 기록이다. 목표 일정이 gate 통과를 보장하지는 않는다.

> **계획한 v0.1.0 기능을 모두 구현하고 검증한 뒤, 정식 PyPI 배포와 동일 릴리스의 Zenodo DOI 공개까지 완료한다. 날짜를 맞추기 위해 기능이나 품질을 줄이지 않는다.**
>
> Deliver the complete agreed v0.1.0 scope, verify it, publish to PyPI, and obtain a public Zenodo DOI for the same release. Move the date when necessary; do not silently reduce scope or quality.

## 1. 기준과 근거 / Baseline and evidence

이 문서는 v0.1.0의 범위·실행 순서·검증·진척에 대한 운영 기준이다. 장기 설계는 마스터 플랜을 따르되, 아래 최신 결정이 과거 일정·축소안보다 우선한다. 원본의 장기 연구·v1.0 목표와 §22의 v0.1.0 조건을 구별한다. 이 문서의 배포 항목이 실행됐다는 의미는 아니다.

### 확인한 근거

| 근거 | 이번 문서에 반영한 내용 | 확인 수준 |
|---|---|---|
| [주제 비교 대화](chatgpt-conversation://6aae35e1-048c-83e8-a4a0-bceec85e78cc) — Master Plan 생성 설명 | FROZEN BASELINE v1.0, 3단계 소스 확장, 분야별 데이터, 보안·출처·영한 문서 | 대화 본문 확인 |
| 같은 대화 — Master Plan v1.1 수정 검토 | MSIS/decay를 첫 릴리스로 이동, 필수 9개 소스, 고급 GNC 분리, 기존 코드 보존 | 대화 본문 확인 |
| 같은 대화 — 넉넉한 첫 릴리스와 quick-look 결정 | `.plot()`, 결과 객체, CLI/Jupyter/Colab, export, health checks | 대화 본문 확인 |
| 같은 대화 — 마지막 사용자 결정 | 일정이 밀려도 계획한 기능 유지; PyPI와 DOI까지 v0.1.0 | 최종 확정 |
| 현재 로컬 자료 | main / 45302e0, source 20개·DB/read-only·격리 15개 검증 | 초기 감사 완료; live/배포 미검증 |
| 사용자 제공 `orbitoby_master_plan.md` | Ultimate Master Plan v2.0 전체 0~55절, software/research 두 트랙 | 원본 대조 완료; byte-identical snapshot은 `ORBITOBY_MASTER_PLAN.md` |

**원본 관리:** 제공된 Obsidian/iCloud 파일은 수정하지 않는다. 원본 경로·SHA-256·전 절 매핑은 `ORBITOBY_MASTER_PLAN_RECONCILIATION.md`에 기록한다. 과거 v1.0 원본/PDF를 확보했다는 뜻은 아니며, 이번에 사용자가 지정한 v2.0을 현 기준으로 삼는다. 원본의 예시·장기 일정·외부 정책 주장을 즉시 실행 지시나 현재 검증된 외부 사실로 취급하지 않는다.

### 결정 우선순위

1. 사용자의 최신 명시적 결정과 이후 승인된 범위 변경.
2. 사용자 제공 Master Plan v2.0의 범위·원칙, 특히 §22의 v0.1.0 정의.
3. 그 범위를 구체화한 이 체크리스트·상세 설계와 승인된 ADR.
4. 오래된 PDF·대화·예시 코드. 충돌 시 최신 기준으로 수정한다.

| 결정 ID | 고정 결정 |
|---|---|
| D01 | 2026-09-30까지 전체 v0.1.0·정식 PyPI 설치 검증·공개 version DOI 완료를 목표로 역산한다. 기존 시간 제약은 제외하며 G0~G4·기능·품질은 면제하지 않는다. |
| D02 | 작은 alpha를 먼저 내고 MSIS 등을 나중으로 미루는 옛 계획은 폐기한다. |
| D03 | Science Day는 대표 사용 사례. 패키지를 행사 전용으로 축소하지 않는다. |
| D04 | v1.0으로 발전 가능한 아키텍처와 정확성을 우선한다. 기존 코드는 적합성에 따라 유지·수정·교체하고 사용자 raw/DB와 API 호환은 회귀·migration으로 보호한다. |
| D05 | MSIS density, altitude/decay/drag 관련 기본 파생량과 `.plot()`은 필수다. |
| D06 | 기존 필수 9개를 유지하며, v2.0 §22에 따라 연구 우선 후보 전체를 admission 평가하고 통과한 소스는 0.1.0에 포함한다. |
| D07 | 코드 Apache-2.0, Toby 사진·마스코트 별도 권리, 외부 데이터 원래 조건 유지. 과거 MIT 제안은 대체된다. |
| D08 | 공개 설명·사용 안내는 영문/한국어 병기. Python 식별자·스키마 필드는 일관된 영문 사용. |
| D09 | 정식 PyPI `0.1.0` 설치 검증과 공개 Zenodo 버전 DOI 확인 전에는 전체 완료가 아니다. |

## 2. 사용 규칙 / Working rules

- 체크박스는 `[ ]` 미완료, `[x]` 증거까지 확인한 완료를 뜻한다. 진행/차단은 작업 기록의 상태로 표현한다.
- 기존 대화에서 성공했다고 한 기능도 현재 코드와 재현 증거 확인 전에는 완료 처리하지 않는다.
- 항목을 완료할 때 같은 커밋 또는 작업 기록에 테스트·문서·결과 링크를 남긴다. 비밀번호, 토큰, 제한된 raw 데이터는 증거에 붙이지 않는다.
- 완료 기준은 구현 + 적절한 검증 + 사용자 문서 + 필요한 보안/라이선스 처리다. 함수 이름이나 TODO만 있는 구현은 완료가 아니다.
- 변경된 코드로 기존 증거가 무효화되면 관련 체크를 다시 연다. 테스트 실패를 숨기거나 필수 항목을 삭제해 완료율을 올리지 않는다.
- ID는 유지한다. 작업 분할은 `API-04a` 같은 하위 ID로 하고 원래 범위를 보존한다.
- 작업 시작: 이 문서 → 최근 기록 → 차단 항목 → 다음 작업 순으로 읽는다. 작업 종료: 체크·증거·차단 사유·다음 시작점을 갱신한다.
- 실제 저장소로 가져갈 때 권장 경로는 `docs/ORBITOBY_V0.1.0_CHECKLIST.md`. 복사 이후 하나만 운영본으로 지정하고 나머지는 스냅샷으로 표시한다.
- 마스터 플랜에는 원칙, 이 문서에는 실행 상태, ADR에는 설계 선택 이유를 기록한다. 범위 변경은 사용자 결정 기록 없이 하지 않는다.

### 작업·증거 기록 양식

| ID | 상태(todo/doing/blocked/done) | 담당 | commit/PR | 검증 명령·결과 또는 증거 경로 | 문서 | 완료일/차단 사유 |
|---|---|---|---|---|---|---|
| 예: API-04 | todo | 미지정 | — | — | — | — |

## 3. 고정 범위 / Frozen scope

| 영역 | 반드시 포함 | 완료 검증 위치 |
|---|---|---|
| 수집·보존 | 인증/기간 수집, source policy, immutable raw, SHA-256, manifest, dedup, coverage/cache | ARC, SRC, HTTP |
| 표준 데이터 | object/identifiers/aliases/orbit/physical/mission/launch/radio/space_weather_series/events/reentry/source_records/licenses/provenance와 derived lineage | DB, ID, DER |
| 소스 | Space-Track, CelesTrak, NOAA SWPC, GCAT, SatNOGS, Launch Library, NASA SPDF/OMNI, GFZ, Canada F10.7 | SRC |
| 확장·계정 | `add_http_source()`, SourceAdapter, 영구 등록, entry-point plugin, trust, runtime/keyring/env/Colab Secrets | EXT, AUTH |
| 조회 | `fetch()`, `object()`, `orbit()`, `space_weather()`, `window()`, `timeseries()`, `search()`, `derive()` | API, DER |
| 연구 | F10.7 observed/adjusted, SSN, Kp/ap/Ap, Dst, AE; MSIS 밀도; 고도·감쇠율·기본 항력 파생량 | SRC, DER, E2E |
| 결과·표시 | data/meta/provenance, credits/license report, pandas/CSV/Parquet, 간단한 `.plot()` | OUT, PLOT |
| 사용·품질 | Python/CLI/Jupyter/Colab/Drive, 영한 문서, pytest/Ruff/CI, 보안/라이선스/health checks | UX, DOC, QA |
| 공개 완료 | GitHub release, 정식 PyPI, clean install, 동일 버전 Zenodo DOI | REL, DOI, DONE |

### 필수 소스와 추가 후보

필수 9개 소스는 실제 동작하는 adapter와 공통 admission 검증을 갖춰야 한다. 물리특성·SSN·Dst·AE 등 필수 연구 변수는 admission을 통과한 지원 소스에서의 공급 경로를 증명한다. 공급 불가능하면 차단 이슈로 기록하고 해결한다.

DONKI, DISCOS, WDC Kyoto, SILSO는 **연구 우선 admission 평가 대상**이다. 원본 §22에 따라 admission을 통과한 항목은 v0.1.0에 포함한다. 시간 부족·선호만으로 통과 소스를 제외하지 않는다. 통과 전에는 지원 완료로 표시하지 않으며, 실제 약관·접근·검증 차단은 근거와 영향·해결 조건을 남긴다. 단순 보류 표기가 필수 연구 변수 누락이나 구현 지연을 면제하지 않는다.

full OD, covariance propagation, guidance/control, 고급 maneuver reconstruction, S3/hosted archive, GUI, 완전한 Python plugin sandbox, 모든 데이터 사이트 지원, software paper 게재는 v0.1.0 필수 범위 밖이다. 간단한 SGP4 검증 helper의 필요 여부는 파생량 설계에서 판단하며 전체 전파 엔진을 만들지 않는다.

### 의존 순서와 게이트

`감사/회귀 → 메타데이터/HTTP → 계정/확장 → 저장/스키마/identity → 소스 → API → 연구/결과/plot → 사용환경/문서 → 통합검증 → 배포 → DOI`

보안·문서·테스트는 각 단계에서 함께 진행한다. 일정은 작업량·차단 사항을 실측해 갱신하며, 날짜 경과만으로 게이트를 통과시키지 않는다.

| 게이트 | 통과 조건 | 이후 가능 작업 |
|---|---|---|
| G0 | 원본 대조와 현재 코드 감사, 회귀 기준 확보 | 구조 변경 |
| G1 | HTTP/auth/plugin/raw/schema/identity 검증 | 전체 소스 및 통합 조회 확정 |
| G2 | 필수 소스·API·derived·plot·export 동작 | 기능 동결과 RC 검증 |
| G3 | E2E·보안·문서·패키징·환경 검증 통과 | 정식 게시 |
| G4 | PyPI 설치 및 DOI 공개 검증 | v0.1.0 완료 선언 |

## 4. 감사와 기존 동작 보존 / Audit & regression

- [x] AUD-01 실제 repo 경로·branch·HEAD·작업 중 변경·remote를 기록한다. 현재 workspace와 코드 repo를 구별한다.
- [x] AUD-02 사용자가 지정한 Master Plan v2.0을 확보해 버전/수신일/해시를 기록하고 대조한다. 과거 Blueprint는 현 기준을 대체하지 않는다. 증거: `ORBITOBY_MASTER_PLAN_RECONCILIATION.md`.
- [x] AUD-03 원본 요구사항 → 체크리스트 ID 대조표를 만든다. 누락·충돌·후속 범위를 명시한다. 증거: 대조 보고서의 원본 §0~55 전체 매핑.
- [x] AUD-04 현 기준을 사용자 제공 v2.0으로 고정하고 원본 snapshot과 파생 설계/체크리스트의 운영본 경로·우선순위를 명시한다. 원본 bytes는 변경하지 않는다.
- [x] AUD-05 service/config/archive/warehouse/identity/catalogue/CLI/adapter의 실제 역할·호출 관계를 조사한다.
- [x] AUD-06 현재 함수별 유지/이동/분해/폐기와 호환성 계획을 기록한다. 재작성 필요성은 증거로 설명한다.
- [x] AUD-07 현재 DB tables/schema/version/row count와 raw/coverage 연결을 읽기 전용으로 조사한다.
- [ ] AUD-08 `.orbitoby` 보존·백업·복구 절차를 만든다. 사용자 데이터를 테스트용으로 덮어쓰지 않는다.
- [ ] AUD-09 옛 package/env/path 이름 잔여와 import/설치 상태를 점검한다.
- [ ] AUD-10 기존 테스트·빌드·Ruff를 실행해 baseline 결과와 환경을 기록한다.
- [ ] AUD-11 대화의 NORAD 228, 2020-01-01~12, 17-record 성공 사례를 보존 fixture로 회귀검증한다. 현재 live 반환 건수를 17로 강제하지 않는다.
- [ ] AUD-12 같은 요청 재실행 시 네트워크 요청 없이 같은 저장 결과를 반환하는지 검증한다.
- [ ] AUD-13 기존 6개 adapter의 실제 상태를 개별 확인한다. registry에 이름이 있다는 사실을 동작 완료로 간주하지 않는다.
- [ ] AUD-14 GitHub 공개 여부와 최초 공개 증거를 실측한다. 과거 remote 미설정 설명을 현재 사실로 사용하지 않는다.

## 5. 저장소·정책·권리 / Repository & source contracts

- [ ] GOV-01 Apache-2.0 LICENSE, 필요한 NOTICE, 저작권자 표기를 정리한다.
- [ ] GOV-02 Toby 자산의 별도 권리·파일 경계와 배포 포함 여부를 명시한다.
- [ ] GOV-03 외부 데이터와 fixture의 이용조건을 코드 라이선스와 분리한다.
- [ ] GOV-04 `.env`, credentials, DB/raw/cache, notebook 출력 및 build 파일의 Git 추적 여부와 ignore 규칙을 확인한다.
- [ ] GOV-05 현재 파일·Git history·배포물 secret scan을 실행한다. 유출 발견 시 폐기/교체/정리 후 재검증한다.
- [ ] GOV-06 GitHub CI, dependency update, issue/PR template, 보안 신고 경로를 구성한다.
- [ ] GOV-07 branch/release 보호와 최소 workflow 권한을 설정하고 검증한다.
- [ ] GOV-08 소스 health check를 cache·rate policy에 맞게 설계하고 외부 장애와 코드 회귀를 구분해 기록한다.
- [ ] META-01 SourceMetadata에 안정 ID, 표시명, homepage, 문서/약관 URL, categories/datasets, auth 요구를 정의한다.
- [ ] META-02 데이터셋별 license/attribution/citation, 재배포 조건, 확인일·근거 URL·검토자를 기록한다.
- [ ] META-03 candidate/experimental/stable/restricted/deprecated/removed 상태의 의미와 전환·승격 기준을 문서화한다.
- [ ] META-04 SourcePolicy에 허용 host, rate/concurrency, cache_ttl, historical_immutable, revision_window, provisional_window, refresh_interval, max_query_span, retry/backoff, 크기/timeout 제한을 둔다.
- [ ] META-05 source가 제공하는 시간범위·cadence·변수·단위·갱신/예보/잠정 상태를 조회 가능하게 한다.
- [ ] META-06 불명확한 라이선스를 허용으로 추정하지 않고 unknown과 제한 사유를 보존한다.
- [ ] META-07 schema 검증과 누락 메타데이터 오류를 테스트한다. 사용된 데이터셋의 정책 버전까지 provenance로 추적한다.

## 6. 공통 HTTP와 계정 / HTTP & credentials

- [ ] HTTP-01 모든 built-in의 네트워크 호출을 공통 client로 이동한다.
- [ ] HTTP-02 TLS 검증, timeout, 응답 크기 제한, streaming 종료 및 연결 정리를 구현한다.
- [ ] HTTP-03 redirect마다 목적지·인증 전달 정책을 검증한다. 타 host로 credential이 새지 않게 한다.
- [ ] HTTP-04 built-in host allowlist와 declarative source URL 검증을 구현한다. loopback/private/link-local 접근은 명시적 정책 없이 허용하지 않는다.
- [ ] HTTP-05 429/Retry-After, 일시적 오류, source별 중단 규칙, 최대 retry를 검증한다. 무한 재시도하지 않는다.
- [ ] HTTP-06 인증 오류·권한 거절·없는 데이터·형식 변경·서비스 장애를 구별한다.
- [ ] HTTP-07 request signature는 비밀값을 제외해 안정적으로 생성한다. query/body/header/exception 로그를 redaction한다.
- [ ] HTTP-08 raw manifest와 오류 메시지에 password/token/cookie/Authorization이 남지 않는지 검증한다.
- [ ] HTTP-09 병렬 요청에서도 source별 rate/concurrency 제한이 적용되는지 검증한다.
- [ ] HTTP-10 local mock server로 redirect·큰 응답·timeout·429·5xx·잘못된 payload를 재현한다.
- [ ] AUTH-01 원본 §6의 runtime → OS keyring → environment → Colab Secrets → .env 개발 호환 순서를 구현·검증하고 충돌/오류 처리를 ADR로 기록한다.
- [ ] AUTH-02 사용자의 자체 계정을 쓰는 흐름을 구현한다. 개발자 공용 계정을 내장하지 않는다.
- [ ] AUTH-03 계정 설정/상태 확인/갱신/삭제를 제공하고 출력은 마스킹한다.
- [ ] AUTH-04 영구 비밀 저장은 keyring을 우선하고 불가능한 환경은 runtime/env/Secrets 사용을 안내한다. 평문 저장으로 조용히 전환하지 않는다.
- [ ] AUTH-05 Space-Track login/session expiry/logout 및 실패 후 재인증을 검증한다.
- [ ] AUTH-06 credential을 registry, manifest, export, notebook 출력, package에 저장하지 않는지 확인한다.
- [ ] AUTH-07 인증 없는 공개 소스는 계정 설정 없이 즉시 사용 가능함을 검증한다.

## 7. 사용자 소스와 플러그인 / Extensibility

- [ ] EXT-01 SourceAdapter fetch/normalize/metadata/policy 계약과 호환 버전을 고정한다.
- [ ] EXT-02 `add_http_source()`로 JSON/CSV/TSV/API URL, 필드·시간·단위 매핑을 선언형으로 등록한다.
- [ ] EXT-03 선언형 설정에서 eval/임의 Python 실행 없이 공통 HTTP·파서 정책을 적용한다.
- [ ] EXT-04 source 1회 등록 → 프로세스 재시작 → 재사용을 검증한다.
- [ ] EXT-05 runtime 전용과 persistent 등록, 조회, 수정, 비활성화, 삭제를 구별한다.
- [ ] EXT-06 registry에 비밀값 대신 credential 참조를 저장하고 원자적 쓰기·손상 복구를 구현한다.
- [ ] EXT-07 built-in/user/plugin 이름 충돌을 조용한 덮어쓰기 없이 처리한다.
- [ ] EXT-08 `orbitoby.sources` entry point를 import 없이 발견하고 출처·버전·trust 상태를 표시한다.
- [ ] EXT-09 Python plugin은 최초 명시적 trust 전 import/실행하지 않는다. 비대화형 환경에서 자동 승인하지 않는다.
- [ ] EXT-10 신뢰 저장·철회 및 plugin 버전/배포 변경 시 재검토 정책을 정의하고 검증한다.
- [ ] EXT-11 plugin 로드 실패가 다른 정상 source 전체를 중단하지 않도록 오류를 격리한다.
- [ ] EXT-12 Python plugin은 사용자 권한으로 실행되며 완전 sandbox가 아님을 영한 안내에 명시한다.
- [ ] EXT-13 최소 선언형 예제와 별도 설치 가능한 테스트 plugin으로 발견→trust→수집→삭제를 끝까지 검증한다.

## 8. 원본·캐시·표준 저장 / Archive & canonical warehouse

- [ ] ARC-01 raw bytes를 불변 artifact로 저장하고 SHA-256을 계산한다.
- [ ] ARC-02 manifest에 source/dataset, 비밀 제거 요청, 수집 시각, content type, hash, adapter/parser version을 기록한다.
- [ ] ARC-03 동일 raw 중복과 동일 요청의 갱신된 응답을 구별한다. 수정된 제공자 데이터가 옛 raw를 덮어쓰지 않게 한다.
- [ ] ARC-04 중단된 다운로드·정규화 실패·부분 저장에 coverage 완료 표시가 생기지 않게 한다.
- [ ] ARC-05 요청 구간, 실제 관측 범위, 검증된 무자료 구간을 구별한다. 오류를 빈 성공으로 cache하지 않는다.
- [ ] ARC-06 겹치는 기간은 이미 있는 구간을 재사용하고 없는 구간만 요청한다.
- [ ] ARC-07 TTL, force refresh, offline, stale cache 사용 여부를 정책으로 명시한다.
- [ ] ARC-08 재시작 후 raw/DB/coverage가 동일하게 재사용되는지 검증한다.
- [ ] ARC-09 hash 불일치·manifest 유실을 감지하고 안전한 복구 또는 오류를 제공한다.
- [ ] ARC-10 같은 raw에서 정규화 재실행이 가능하고 parser 변경 이력을 보존한다.
- [ ] DB-01 objects/identifiers/orbit/physical/mission/launch/radio/space_weather/reentry/provenance의 canonical 계약을 정의한다.
- [ ] DB-02 derived 결과와 transform/input lineage를 저장하는 구조를 정의한다.
- [ ] DB-03 각 필드에 type/unit/null 의미/time basis/source reference/quality flag를 정의한다.
- [ ] DB-04 관측 시각, epoch, 유효 기간, 제공자 갱신 시각, 수집 시각을 구별한다.
- [ ] DB-05 UTC·시간구간 경계·정렬·중복·숫자 정밀도 규칙을 ADR로 확정한다.
- [ ] DB-06 안정적 PK/FK, artifact 참조, 중복 삽입·upsert 정책과 충돌 보존을 구현한다.
- [ ] DB-07 기존 orbit_elements/artifacts/coverage에서 schema version 기반 migration을 구현한다.
- [ ] DB-08 백업→migration→row/hash 검증→실패 복구를 복제 DB로 검증한다.
- [ ] DB-09 query parameter binding과 읽기/쓰기 lifecycle, context manager, 동시 접근 제한을 검증한다.
- [ ] DB-10 local 데이터 root 변경·권한 오류·손상 DB에서 이해 가능한 오류를 제공한다.
- [ ] ID-01 NORAD/COSPAR/provider ID를 원형과 정규화 값으로 보존한다.
- [ ] ID-02 여러 소스의 동일 물체를 연결하고 ID 없는 자료도 원본 추적 가능하게 유지한다.
- [ ] ID-03 이름만으로 무조건 병합하지 않고 ambiguous/unresolved 상태를 표현한다.
- [ ] ID-04 충돌 후보와 선택 근거·source 우선순위를 노출한다. 낮은 우선순위 자료를 삭제하지 않는다.
- [ ] ID-05 재수집·순서 변경·중복 자료에서도 stable object identity를 검증한다.
- [ ] ID-06 잘못된 식별자, 서로 상충하는 식별자, 이름 변경 사례를 테스트한다.

## 9. 소스 통합 / Source integration

각 필수 소스는 아래 공통 admission 항목 ADM-01~08을 **각각** 통과해야 한다. source별 결과는 뒤의 매트릭스에 증거를 연결한다.

- [ ] ADM-01 공식 endpoint·dataset·API 문서·지원 시간범위·변수를 확인한다.
- [ ] ADM-02 약관·인용·재배포·자동 접근·rate policy를 공식 근거와 확인일로 기록한다. 과거 대화의 라이선스 설명만 복사하지 않는다.
- [ ] ADM-03 인증·수집·pagination/chunking·raw 보존·canonical 매핑을 구현한다.
- [ ] ADM-04 단위·시간·fill value·결측·provisional/predicted 상태와 개정 데이터를 정확히 보존한다.
- [ ] ADM-05 재배포 가능한 fixture 또는 합성 fixture로 parser·오류·경계 테스트를 수행한다.
- [ ] ADM-06 제한된 live smoke와 두 번째 cache hit를 검증하고 실행일을 기록한다.
- [ ] ADM-07 result→record→artifact→source/license까지 provenance가 연결되는지 확인한다.
- [ ] ADM-08 영한 source 문서·credential/rate 안내·현재 건강 상태와 지원 한계를 작성한다.

| 필수 source | 0.1.0 핵심 검증 | admission 결과/증거 |
|---|---|---|
| Space-Track | 사용자 인증, historical GP, 범위 분할, cache/coverage | 미검증 |
| CelesTrak | 지원 GP 형식·ID·epoch, 갱신/호출 정책 | 미검증 |
| NOAA SWPC | 선택 제품과 필드, 관측/예측/잠정 구분 | 미검증 |
| GCAT | 물체·물리특성·발사·재진입 중 지원 필드와 identity | 미검증 |
| SatNOGS | catalogue/radio 및 지원 orbit 자료, 이전 TLE 오류 재검증 | 미검증 |
| Launch Library | 발사/임무, pagination, provider ID 연결 | 미검증 |
| NASA SPDF/OMNI | 실제 dataset/variables, 장기 시계열, 단위/fill values | 미검증 |
| GFZ | Kp·ap·Ap 구별, cadence와 확정/잠정 상태 | 미검증 |
| Canada F10.7 | observed/adjusted 구별, 날짜/단위/측정 및 갱신 상태 | 미검증 |

- [ ] SRC-01 Space-Track admission을 완료한다.
- [ ] SRC-02 CelesTrak admission을 완료한다.
- [ ] SRC-03 NOAA SWPC admission을 완료한다.
- [ ] SRC-04 GCAT admission을 완료한다.
- [ ] SRC-05 SatNOGS admission을 완료한다.
- [ ] SRC-06 Launch Library admission을 완료한다.
- [ ] SRC-07 NASA SPDF/CDAWeb/HAPI의 접근 경로를 선택·기록하고 OMNI admission을 완료한다. 모든 transport 구현을 자동 요구하지 않는다.
- [ ] SRC-08 GFZ admission을 완료한다.
- [ ] SRC-09 Canada F10.7 admission을 완료한다.
- [ ] SRC-10 F10.7 observed/adjusted, SSN, Kp, ap, Ap, Dst, AE 각각의 공급 dataset·field·unit·coverage 매핑을 완성한다.
- [ ] SRC-11 physical mass/size/shape/area 및 관련 특성의 공급 경로·단위·결측·추정 여부를 검증한다. 없는 값을 만들어 채우지 않는다.
- [ ] SRC-12 같은 변수의 여러 소스 값이 다르면 공존시키고 사용자 선택과 기본 우선순위를 설명한다.
- [ ] SRC-13 DONKI/DISCOS/Kyoto/SILSO 각각에 ADM-01~08을 적용하고 pass/blocked와 증거·영향을 기록한다. 통과한 소스는 0.1.0에 포함해 E2E·문서·export를 검증한다.

후보 기록: `source | 평가일 | ADM-01~08 증거 | 연구 필요 | pass/blocked | 구현 ID | 포함 버전/차단 해결 조건`.

일시적 외부 장애는 코드 미완성과 구별한다. 필수 소스를 experimental로 이름만 바꿔 통과시키지 않는다. 충분한 최근 live 증거·fixture·복구 검증이 있어 일시 장애로 판단되는 경우만 판단 근거와 재확인 조건을 기록한다. 핵심 동작을 입증하지 못하면 출시 차단이다.

## 10. 공개 API / Public API

- [ ] API-01 `Archive()`의 data root, 설정, context manager, 연결 종료를 안정화한다.
- [ ] API-02 `sources_available()`에서 종류·capability·auth·trust·지원 상태를 확인할 수 있게 한다.
- [ ] API-03 `fetch()`가 지정 source/dataset/기간을 수집하고 raw·coverage·정규화 결과와 연결되게 한다.
- [ ] API-04 `object()`가 NORAD/COSPAR/provider ID로 기본정보와 분야별 정보를 반환한다. 충돌·없는 분야를 표현한다.
- [ ] API-05 `orbit()`가 역사적 기간과 source 선택, epoch 정렬, 빈 구간·coverage를 정확히 반환한다.
- [ ] API-06 `space_weather()`가 필드·기간·source 선택과 품질/단위를 유지한다.
- [ ] API-07 `window()`가 orbit/physical/space_weather 등 선택 분야를 같은 연구 구간에 묶고 분야별 결과를 제공한다.
- [ ] API-08 `timeseries()`가 namespaced fields, cadence, 정렬·집계 규칙을 제공한다.
- [ ] API-09 시간 정렬의 exact/as-of/tolerance/resample 의미를 정하고 look-ahead·무단 보간을 방지한다.
- [ ] API-10 `search()`가 실제 canonical 필드에 대해 검색·필터·정렬·limit을 수행한다. 전체 결과를 무시하고 고정값을 반환하지 않는다.
- [ ] API-11 잘못된 field/category/ID/기간/timezone 입력의 일관된 예외와 영한 안내를 제공한다.
- [ ] API-12 데이터 없음, 권한 없음, coverage 미확보, source 장애를 서로 구별한다.
- [ ] API-13 다중 source/다중 object 요청의 결과 구조와 부분 실패 정책을 문서화한다.
- [ ] API-14 공통 결과 객체의 data/meta/provenance 및 분야별 접근을 구현하고 최종 이름·타입을 문서화한다.
- [ ] API-15 각 public API의 정상·빈 결과·실패 사례를 테스트하고 예제를 실행한다.

## 11. 과학 파생량 / Scientific transforms

- [ ] DER-01 `derive()` 또는 동등한 공개 인터페이스의 transform 입력/출력·의존성·버전 계약을 고정한다.
- [ ] DER-02 mean motion/궤도요소로 계산하는 altitude의 정의·상수·단위를 명시한다. 평균 고도를 순간 고도로 표현하지 않는다.
- [ ] DER-03 altitude 변화와 `dh/dt`의 부호·시간창·불규칙 표본·결측 처리 규칙을 구현한다.
- [ ] DER-04 중복 epoch/큰 시간 간격/이상값/기동 가능 구간에서 계산 제한·flag를 남긴다.
- [ ] DER-05 MSIS 구현·버전·라이선스·dependency 지원 환경을 선택하고 ADR에 기록한다.
- [ ] DER-06 MSIS 입력 UTC/위도/경도/고도와 F10.7/평균 F10.7/Ap 이력 요구를 선택 모델 기준으로 검증한다.
- [ ] DER-07 입력 위치의 출처 또는 계산 방식과 필요한 좌표/시간 변환을 명시한다. 고도만으로 밀도를 결정하지 않는다.
- [ ] DER-08 MSIS 밀도 단위를 통일하고 model output임을 표시한다. 관측 density로 저장하지 않는다.
- [ ] DER-09 신뢰 가능한 모델 예제 또는 기준값에 대해 단위·수치 허용오차를 검증한다.
- [ ] DER-10 기본 drag 관련 출력 목록과 식을 고정한다. mass/area/Cd/BC 정의·속도·가정·단위를 명시한다.
- [ ] DER-11 물리특성이 없으면 계산 불가/사용자 입력/명시적 가정을 구별한다. TLE B*를 무조건 물리적 BC로 취급하지 않는다.
- [ ] DER-12 모든 파생 결과에 입력 artifact/record, transform/model version, 설정, 상수, 품질 flag를 연결한다.
- [ ] DER-13 알려진 합성 궤도와 단위 변환 사례로 altitude/decay/drag를 검증한다.
- [ ] DER-14 동일 입력·모델·설정 재실행의 재현성과 cache 무효화 조건을 검증한다.
- [ ] DER-15 MSIS/decay/drag 예제를 연구 workflow에 연결하고 적용 한계를 영한 문서에 쓴다.

## 12. 결과·내보내기·시각화 / Results, export & plotting

- [ ] OUT-01 `.to_pandas()`에서 timezone·단위 metadata·결측·원본 result 불변성을 검증한다.
- [ ] OUT-02 CSV/Parquet export를 구현하고 round-trip 시 주요 값·타입·시간이 유지되는지 확인한다.
- [ ] OUT-03 데이터와 함께 provenance/citation/license manifest를 내보낸다. CSV처럼 metadata가 약한 형식은 sidecar를 제공한다.
- [ ] OUT-04 `.credits()`와 `.license_report()`가 실제 결과에 사용된 source/dataset만 반영한다.
- [ ] OUT-05 결과가 여러 이용조건을 포함하면 각 조건과 재배포 제한을 보존한다. 결과 전체를 Apache-2.0 데이터라고 표시하지 않는다.
- [ ] OUT-06 unknown/restricted 조건의 경고·차단/명시적 처리 정책을 정하고 정상 연구용 로컬 사용 흐름도 검증한다.
- [ ] OUT-07 외부 데이터 fixture/export 예시를 공개해도 되는지 배포 직전에 재확인한다.
- [ ] OUT-08 export에 비밀값과 사용자 개인 경로가 불필요하게 포함되지 않는지 검증한다.
- [ ] PLOT-01 `.plot()` 기본 x축을 time으로 고정하고 단일 numeric series 선 그래프를 구현한다.
- [ ] PLOT-02 같은 unit의 여러 series는 한 panel, 다른 unit은 분리 panel로 그린다.
- [ ] PLOT-03 시간 정렬·결측 gap·빈 결과·non-numeric fields·unit 미상 사례를 처리한다. 임의 보간하지 않는다.
- [ ] PLOT-04 title/fields 정도의 최소 옵션과 Figure/Axes 반환 방식을 정한다.
- [ ] PLOT-05 이름·단위·범례를 명확히 표시하고 provisional/predicted 등 상태 metadata를 유지한다.
- [ ] PLOT-06 matplotlib core dependency 또는 extra 여부를 ADR로 확정한다. 과거 논의의 선호를 확정 사실로 간주하지 않는다.
- [ ] PLOT-07 notebook 표시·headless 저장·여러 unit·결측 사례를 검증한다.
- [ ] PLOT-08 고급 시각화는 pandas export로 이어지는 영한 예제를 제공한다.

## 13. CLI·노트북·저장 환경 / User experience

- [ ] UX-01 현재 CLI를 감사하고 sources/fetch/query/export/auth/plugin 관리 중 공개할 명령을 확정한다.
- [ ] UX-02 CLI가 Python API와 같은 정책·오류·cache를 사용하게 하고 영한 help·적절한 exit code를 제공한다.
- [ ] UX-03 CLI에서 credential을 명령행 인자·history에 노출하지 않는 설정 흐름을 검증한다.
- [ ] UX-04 Jupyter 새 kernel에서 수집→조회→plot→export 예제를 실행한다.
- [ ] UX-05 Colab 새 runtime에서 pip 설치, 공개 source, Colab Secrets 인증, MSIS/plot/export를 실행한다.
- [ ] UX-06 Colab/Google Drive의 지속 저장과 runtime 재시작 후 archive 재사용을 검증한다.
- [ ] UX-07 Drive 환경의 DB 잠금·동시 접근 제약을 확인하고 안전한 local 작업/동기화 절차를 문서화한다.
- [ ] UX-08 사용자 지정 data root와 공백/비ASCII 경로를 검증한다.
- [ ] UX-09 offline cache 사용과 네트워크 복구 후 갱신 예제를 제공한다.

## 14. 영한 문서와 운영 / Documentation

- [ ] DOC-01 README 영/한: 정체성, 설치, quickstart, 지원 기능·제약, 계정, citation을 작성한다.
- [ ] DOC-02 SECURITY 영/한: 비밀정보 처리, plugin trust, 신고 경로·지원 버전을 작성한다.
- [ ] DOC-03 SOURCES 영/한: 필수/후보 상태, endpoint, 데이터별 라이선스·인용·rate·확인일을 작성한다.
- [ ] DOC-04 CONTRIBUTING 영/한: 개발환경, 테스트, adapter admission, schema/ADR 규칙을 작성한다.
- [ ] DOC-05 주요 CLI help, issue/PR template, 오류 해결 안내와 공개 소개를 영한으로 맞춘다.
- [ ] DOC-06 API·결과 객체·units/time semantics·derived assumptions를 설명한다.
- [ ] DOC-07 선언형 소스·persistent adapter·plugin·credential별 사용 예제를 작성한다.
- [ ] DOC-08 migration/backup/restore/cache/force refresh/아카이브 위치 안내를 작성한다.
- [ ] DOC-09 Science Day 전체 예제를 제공하되 통계적 인과·민감도 분석 자체는 연구 코드의 역할로 명시한다.
- [ ] DOC-10 모든 문서 예제를 release candidate에서 실행하고 존재하지 않는 API·placeholder를 제거한다.
- [ ] DOC-11 CHANGELOG와 v0.1.0 release notes에 기능·지원 소스·한계·migration·설치·인용을 기록한다.
- [ ] DOC-12 사용자 질문 없이도 재현 가능한 bug report 양식과 source health 진단 방법을 제공한다.

## 15. 품질 및 통합 수용 시험 / Quality & acceptance

- [ ] QA-01 offline deterministic unit/fixture/integration 테스트와 credential이 필요한 live 테스트를 분리한다.
- [ ] QA-02 pytest·Ruff·import·build 검사를 CI에서 통과시킨다.
- [ ] QA-03 지원 Python 최저/주요 버전과 Windows/macOS/Linux 지원 범위를 선언하고 해당 설치·핵심 테스트를 실행한다.
- [ ] QA-04 secret redaction, untrusted plugin, unsafe URL/redirect, SQL binding, archive 경로 안전성 테스트를 통과시킨다.
- [ ] QA-05 dependency/security audit에서 출시 차단 취약점을 해결하고 판정 근거를 남긴다.
- [ ] QA-06 fixture의 재배포 권리와 dependency/model license 및 배포물 NOTICE를 확인한다.
- [ ] QA-07 기간 경계·윤일·UTC·missing/sentinel·source conflict·개정 자료 회귀를 검증한다.
- [ ] QA-08 대표 장기간·다중 물체 조회의 실행시간/메모리·요청수를 측정하고 실용적인 한계와 chunk 정책을 문서화한다.
- [ ] QA-09 offline 테스트가 네트워크나 개발자 `.orbitoby`/계정 설정에 의존하지 않음을 확인한다.
- [ ] QA-10 실패·차단·known limitation을 공개 상태와 일치시키고 핵심 미완료를 known issue로 면제하지 않는다.

다음 E2E는 새 환경·새 data root에서 수행하며, commit/version, 실행일, 환경, 데이터 구간·대상, 결과 해시/허용오차, 증거 위치를 기록한다. 작은 회귀 fixture와 실제 연구 구간 검증을 구별한다.

- [ ] E2E-01 새 환경에서 설치하고 `from orbitoby import Archive`를 실행한다.
- [ ] E2E-02 인증 없는 source를 즉시 수집하고 raw/hash/manifest/canonical/provenance를 확인한다.
- [ ] E2E-03 사용자 Space-Track 계정으로 historical orbit을 수집한다.
- [ ] E2E-04 동일 요청 재실행과 일부 겹치는 기간 요청에서 cache/coverage가 정상 동작한다.
- [ ] E2E-05 같은 물체를 NORAD/COSPAR로 조회해 identity와 physical/mission/launch/radio/reentry 지원 결과를 확인한다.
- [ ] E2E-06 F10.7/SSN/Kp/ap/Ap/Dst/AE를 실제 지원 기간으로 조회해 변수별 출처·결측·단위를 확인한다.
- [ ] E2E-07 `window()`로 분야를 묶고 `timeseries()`로 시간축을 정렬한다.
- [ ] E2E-08 MSIS 밀도·고도·감쇠율·기본 drag 파생량을 계산하고 입력 lineage를 추적한다.
- [ ] E2E-09 `.plot()`으로 단일·동일 단위 다중·상이한 단위 다중 시계열을 확인한다.
- [ ] E2E-10 pandas/CSV/Parquet와 credits/license/provenance를 export하고 다시 읽어 대조한다.
- [ ] E2E-11 프로세스 재시작·offline 재조회에서 저장 archive와 persistent user source를 재사용한다.
- [ ] E2E-12 별도 plugin 설치→발견→trust→실행→철회와 미신뢰 차단을 검증한다.
- [ ] E2E-13 CLI와 Jupyter/Colab 각각에서 대표 흐름을 실행한다.
- [ ] E2E-14 Science Day 대상/연구기간을 명시하고 실제 dataset 생성 절차를 재현한다. 제공자 coverage가 없는 기간을 성공으로 꾸미지 않는다.
- [ ] E2E-15 오류·일시 장애·credentials 부재 상황에서 원본 손상이나 허위 coverage가 생기지 않는지 확인한다.

## 16. 패키징과 PyPI / Packaging & publication

계정·설정 준비는 앞당겨도 된다. 게시할 산출물은 G3 통과 commit에서 생성한다. PyPI Trusted Publishing은 OIDC를 이용한 단기 인증을 지원한다. [공식 안내](https://docs.pypi.org/trusted-publishers/)

- [ ] REL-01 실제 PyPI 프로젝트명 `orbitoby`의 소유/사용 가능 상태와 계정 권한을 확인한다. 이름 충돌은 차단 이슈로 해결한다.
- [ ] REL-02 pyproject의 version `0.1.0`, Python 범위, dependencies/extras, description, license, URLs를 정합하게 설정한다.
- [ ] REL-03 wheel/sdist에 필요한 코드·schema·라이선스·자료만 포함하고 secret/개인 raw/DB가 없는지 검사한다.
- [ ] REL-04 sdist에서 다시 wheel을 만들고 editable 설치 없이 clean environment에서 설치·import·핵심 흐름을 검증한다.
- [ ] REL-05 TestPyPI에서 배포 절차와 설치를 시험한다. dependency 출처를 명시하고 예기치 않은 패키지 혼합을 방지한다.
- [ ] REL-06 GitHub Actions↔PyPI Trusted Publisher의 owner/repo/workflow/environment를 맞추고 release job 권한을 최소화한다.
- [ ] REL-07 CI 검증 artifact를 게시 단계가 그대로 사용하도록 구성하고 wheel/sdist SHA-256을 기록한다.
- [ ] REL-08 G0~G3와 모든 필수 미완료·차단 상태를 검토해 release candidate를 확정한다.
- [ ] REL-09 최종 commit SHA와 `v0.1.0` tag, artifact version이 같은 코드를 가리키는지 확인한다.
- [ ] REL-10 Zenodo 연동/메타데이터 준비(DOI-01~03)를 GitHub release 생성 전에 마친다.
- [ ] REL-11 REL-14의 공개 GitHub Release 생성 후 정식 PyPI에 `0.1.0` wheel/sdist를 게시하고 프로젝트 페이지·파일·해시·metadata를 확인한다.
- [ ] REL-12 별도 새 환경에서 정식 PyPI의 `pip install orbitoby==0.1.0`을 실행해 버전·import·대표 기능을 검증한다.
- [ ] REL-13 기본 `pip install orbitoby`도 현재 정식 버전을 설치하는지 확인한다. 이 증거는 확인일과 함께 기록한다.
- [ ] REL-14 같은 tag/commit으로 공개 GitHub Release를 생성한다(실행 순서: REL-10 → REL-14 → REL-11~13). 영한 notes·artifact를 확인하고 게시 후 PyPI 링크를 보완한다.
- [ ] REL-15 배포 후 smoke 결과를 기록한다. 이미 게시한 버전의 파일이나 tag를 바꿔 오류를 숨기지 않는다.

## 17. Zenodo DOI / Archival completion

GitHub 연동을 통해 release를 아카이브하고 처리 후 레코드를 확인할 수 있다. [공식 release 보존 절차](https://help.zenodo.org/docs/github/archive-software/github-upload/)

- [ ] DOI-01 Zenodo 계정과 대상 GitHub 저장소 연결·활성화를 확인한다.
- [ ] DOI-02 CITATION.cff의 실제 저자·제목·버전·날짜·저장소·라이선스를 작성하고 유효성을 검사한다. 저자/ORCID를 추정하지 않는다.
- [ ] DOI-03 `.zenodo.json`을 사용한다면 CFF와 내용을 맞춘다. 둘 다 있을 때 Zenodo가 `.zenodo.json`을 우선함을 반영한다. [메타데이터 규칙](https://help.zenodo.org/docs/github/describe-software/citation-file/)
- [ ] DOI-04 GitHub `v0.1.0` release의 Zenodo 처리 결과를 확인한다. 실패하면 원인을 해결하고 중복 레코드를 만들지 않는다.
- [ ] DOI-05 수동 보존이 필요하면 같은 release 산출물·commit·해시를 사용하고 자동 보존과 중복되지 않도록 경로를 기록한다.
- [ ] DOI-06 공개 레코드의 title/authors/version/license/files/관련 GitHub·PyPI 링크가 `0.1.0`과 일치하는지 확인한다.
- [ ] DOI-07 실제 버전 DOI를 기록하고 DOI 링크를 열어 공개된 `0.1.0` 레코드로 연결되는지 검증한다. 예약 번호나 draft만으로 완료 처리하지 않는다.
- [ ] DOI-08 concept DOI와 version DOI를 구별해 기록한다. 재현 가능한 버전 인용에는 `0.1.0` version DOI를 사용한다.
- [ ] DOI-09 README·인용 안내·release notes에 DOI를 반영한다. DOI 사후 문서 갱신 때문에 이미 공개한 tag/artifact를 바꾸지 않는다.
- [ ] DOI-10 배포 기록에 PyPI/GitHub/Zenodo URL, commit/tag, artifact hash, 공개일과 확인자를 남긴다.

### 최종 릴리스 기록 / Release record

| 필드 | 값 |
|---|---|
| 상태 | 미완료 — 감사·계획 재점검 완료, G0~G4 미통과 |
| 최종 commit / tag | 미정 / v0.1.0 예정 |
| wheel / sdist SHA-256 | 미기록 |
| GitHub Release URL | 미발행 |
| PyPI version URL | 미발행 |
| 정식 PyPI clean-install 증거 | 미확인 |
| Zenodo public record URL | 미발행 |
| Zenodo version DOI / concept DOI | 미발급 / 미확인 |
| DOI 공개·resolve 확인일 | 미확인 |
| 최종 테스트/보안/라이선스 보고서 | 미작성 |
| 완료 선언일 / 확인자 | 미정 |

## 18. 최종 완료 조건 / Definition of Done

- [ ] DONE-01 필수 범위의 모든 항목이 완료됐고 근거 대조·설계 미결정·출시 차단 문제가 남지 않았다.
- [ ] DONE-02 필수 9개 source와 연구 변수의 실제 공급·사용 흐름이 검증됐다.
- [ ] DONE-03 공개 API, MSIS/decay/drag, plot, export, credentials/plugin, CLI/Jupyter/Colab이 검증됐다.
- [ ] DONE-04 기존 데이터 보존·migration·보안·권리·영한 문서·CI와 E2E를 통과했다.
- [ ] DONE-05 정식 PyPI `0.1.0` 게시와 fresh install 검증이 끝났다.
- [ ] DONE-06 동일 릴리스가 Zenodo에 공개 보존됐고 버전 DOI가 정상 연결된다.
- [ ] DONE-07 최종 기록이 완성됐고 체크리스트 운영본과 release 증거가 저장소에 보존됐다.

완료 계산은 이 일곱 조건의 AND다. PyPI만 끝났거나 DOI가 예약 상태이면 v0.1.0은 아직 진행 중이다. SoftwareX/JOSS 투고·심사와 본 연구 논문 완성은 별도 장기 목표다.

## 19. 미결정·차단·다음 작업 / Live working log

기능 범위는 고정됐지만 아래 구현 선택은 작업 초기에 ADR로 확정한다. 선택이 필요하다는 이유로 해당 기능을 빼지 않는다.

| ID | 미결정/확인 사항 | 해결 시점 | 연결 |
|---|---|---|---|
| OPEN-01 | 해결: 사용자 제공 v2.0 확보·전 절 대조·snapshot 보존 | 2026-09-28 | AUD-02~04 |
| OPEN-02 | 현 상태 재확인 완료; raw 경로/manifest 수리·backfill·정식 회귀 미완료 | G0 이전 | AUD-08~13 |
| OPEN-03 | Python/OS 지원 범위와 dependency 정책 | G1 이전 | QA-03, REL-02 |
| OPEN-04 | 결과 객체·시간 경계·resample·source 선택 계약 | 구현 전 | DB, API |
| OPEN-05 | credential 순서는 v2.0 §6으로 확정; fallback 처리·plugin trust 변경 정책 구현 | 구현 전 | AUTH, EXT |
| OPEN-06 | MSIS backend/version, 위치 입력, drag 출력 목록 | DER 착수 전 | DER-05~10 |
| OPEN-07 | matplotlib core/extra | PLOT 착수 전 | PLOT-06 |
| OPEN-08 | 계정 권한·PyPI 이름·저자 정보·Zenodo 연동 | release 준비 초반 | REL, DOI |

### 다음 세 작업

1. AUD-08/09, DB-08: 일관된 백업·복제본에서 raw/manifest 경로 복구 → reindex → restore·기존 17행/coverage 보존 검증.
2. AUD-10~13: repo 정식 회귀 테스트와 source capability 현황 확립. 새 parser의 reindex skip·generic fetch 저장 차이를 회귀로 기록.
3. 재점검 R02~R06의 API/정규화/identity/source 계약을 검토한 뒤 GOV/META/HTTP 진행. 28일 계정·권한·구조·공통 기반, 29일 전체 기능·RC, 30일 최종 검증·PyPI·DOI 순서로 진행.

### 세션 종료 기록 양식

```text
날짜 / 작업자:
branch / 시작 SHA / 종료 SHA:
완료 ID와 증거:
진행 중 ID와 현재 상태:
실패·차단과 해결 조건:
승인된 ADR/범위 변경:
다음 시작점(최대 3개):
릴리스 예상일과 근거(범위·품질 변경 없음):
```

### 변경 이력

| 날짜 | 문서 버전 | 변경 | 구현 완료 처리 |
|---|---|---|---|
| 2026-09-28 | 1.0 | 확인한 마스터 플랜 설명·v1.1 수정·최신 범위 결정을 통합해 최초 작성 | 없음; 코드 감사 전 |


## 20. 초기 감사 업데이트 / Initial audit update — 2026-09-28

- AUD-01/05/06/07 완료 증거: `ORBITOBY_CURRENT_STATE_AND_CLEANUP.md`, `audit/source_inventory.json`, `audit/warehouse_readonly.json` 및 파일별 disposition matrix.
- 실제 repo: `/Users/jin-yeseo/code/orbitoby`, main, HEAD `45302e0`, 감사 시작 시 clean.
- object/search/records/reindex/identity는 이미 구현돼 있다. API 전체 완료가 아니라 기존 자산으로 확인했다.
- 실제 orbit 17 rows; artifacts 12, coverage 2. identity 관련 tables는 비어 있어 backfill 미완료다.
- raw 12개는 모두 새 root에 있고 해시가 일치하나 DB는 옛 root를 참조한다. path repair와 reindex를 먼저 검증한다.
- 격리 합성 검증 15개 통과; Ruff 19개 진단. live/admission·packaging·전체 security/license 검증은 수행하지 않았다.
- 상세 아키텍처: `ORBITOBY_ARCHITECTURE_V0.1.0.md`. 이후 사용자 제공 v2.0 원본을 확보·대조했다. 명시된 원본 결정은 반영하고 나머지 ADR 후보만 유지한다.
- 다음 작업: 프로젝트 연결 → 복제 DB path repair/backfill 검증 → characterization tests → metadata/HTTP/redaction.


운영본 위치: 실제 Orbitoby 저장소 `docs/`. 이전 사이언스데이 workspace의 파일은 작성 시점 스냅샷이다.

## 21. Master Plan v2.0 누락 보완 / Reconciled requirements

아래는 원본에서 확인한 누락을 구체화한 항목이다. 기존 ID는 보존하며 실제 구현·검증 전에는 완료 표시하지 않는다. 일부 항목은 원본의 최종 품질 목표를 0.1.0의 기반 작업으로 앞당겨 명시한 것이며, v1.0 성숙도나 논문 제출까지 요구하는 것은 아니다.

- [ ] DB-11 내부 object_uid, source-native source_records, aliases, licenses의 계약과 기존 object_id migration을 확정한다.
- [ ] DB-12 space_weather_series와 space_weather_events를 구분한다. event type/start/peak/end/관계 ID/provenance를 정의하고, admission 통과 event source를 실제 연결한다.
- [ ] ID-07 NORAD → COSPAR → trusted cross-ID → documented launch/piece → name candidate의 증거 우선순위와 충돌/후보 처리를 검증한다. 이름만으로 merge하지 않는다.
- [ ] ARC-11 revision/provisional window와 historical_immutable을 coverage 계획에 반영하고 오래된 잠정값이 영구 cache로 굳지 않는지 검증한다.
- [ ] HTTP-11 Orbitoby User-Agent와 5xx circuit/backoff·복구 조건을 테스트한다.
- [ ] EXT-14 JSON/CSV/TSV 선언형 사용자 소스 각각에서 등록→재시작→fetch→단위/시간 mapping을 검증한다.
- [ ] API-16 result.sources가 실제 결과 기여 source만 반영하고 필드 선택·slice 후에도 정확한지 검증한다.
- [ ] API-17 변수별 alignment 계약(nearest/daily_exact/aggregate_max 등)을 구현하고 tolerance/tie/bin 경계를 문서화한다. 무단 interpolate/forward-fill/resample을 하지 않는다.
- [ ] API-18 object_type, mass_kg 범위, altitude_km 범위, inclination_deg 범위, launch_year 범위 검색을 구현한다. 궤도 조건의 평가 시점/구간과 property 충돌 선택 의미를 고정한다.
- [ ] API-19 DuckDB/Parquet 필터·projection pushdown을 검증해 큰 데이터를 먼저 pandas 전체 로딩하지 않게 한다.
- [ ] DER-16 orbital period, semimajor axis, apogee/perigee와 rolling decay metrics를 변환 목록에 포함하고 기준 수치·단위·noise/gap 정책을 검증한다.
- [ ] DER-17 변환 결과에 transform name/version, params, source records, Orbitoby version, creation time을 모두 남긴다.
- [ ] QA-11 type checker를 선택·설정하고 public 계약과 핵심 모듈을 점검한다. 무분별한 ignore로 통과시키지 않는다.
- [ ] QA-12 CodeQL 또는 명시적 동등 static security analysis를 구성하고 위험 진단을 검토한다.
- [ ] QA-13 adapter contract tests를 구축하고 PR은 fixture/mock, 주간 health workflow는 최소 live smoke로 분리한다. 이 체크리스트 작성 자체가 자동화 활성화를 뜻하지 않는다.
- [ ] DOC-13 Getting Started/Installation/Auth/Data Model/API/Plugins/User Sources/Licensing/Citation/Troubleshooting/Governance를 기존 필수 문서와 함께 영한 coverage matrix로 점검한다.
- [ ] GOV-09 AI_USAGE.md에 도구/모델(확인 시), 날짜, 기여 범위, 실제 사람 검토, 검증, 최종 결정자를 기록한다. 미검토를 검토 완료로 기재하지 않는다.
- [ ] GOV-10 source lifecycle과 사람이 내린 주요 설계 결정·근거를 ADR로 남긴다.
- [ ] REL-16 release provenance/attestation 생성·검증 정책을 정하고 배포 산출물·commit과 연결한다.
- [ ] E2E-16 admission을 통과한 추가 연구 소스와 events/추가 derived/범위 검색/TSV user source를 수용 시험에 포함한다.

### 장기 트랙과의 경계

v0.1.0은 §22의 기능 end-to-end + GitHub/PyPI/공개 version DOI다. v1.0 안정성·deprecation 계약·외부 사용자 검증, Science Day QC/통계/논문·재현성 패키지, software paper는 별도 트랙이다. 대조 보고서가 §23~55의 연결을 보존한다. 정책/학술 자격의 최신성은 실제 제출 시 재검증한다.

### 2026-09-28 / 문서 1.1 변경

사용자 제공 Ultimate Master Plan v2.0 전 절 대조. 인증 순서 교정, admission 통과 연구 source 포함 규칙, event/alias/license 모델, 추가 derived/search/result.sources, AI 사용 기록·품질 요구를 반영했다. AUD-02~04만 증거에 따라 완료 처리했으며 새 구현 항목은 모두 미완료다.


## 22. 착수 전 재점검 / 2026-09-28 · 문서 1.2

250개 기존 ID와 완료 체크 7개를 유지한다. 이번 문서 검토로 구현 항목을 완료 처리하지 않았다. ID별 상태·요구문은 `audit/2026-09-28/plan_review_item_status.json`, 재실행 증거는 `plan_review_verification.json`, 세부 보완 계약은 `ORBITOBY_V0.1.0_READINESS_REVIEW.md`에 있다. 새 경쟁 체크리스트를 만들지 않고 기존 ID에 아래 수용 조건을 연결한다.

| 보완 계약 | 연결 ID | 구현 전 추가 수용 조건 |
|---|---|---|
| R01 복구 | AUD-08~12, ARC-08~10, DB-08/10 | 복제본·원상 백업 분리, manifest 경로도 수리, 재시도·restore·운영 경로 검증 |
| R02 정규화 버전 | ARC-10, DB-06/07/11, ID-05, DER-12/17 | run/version/context/원본 locator, 새 parser와 단순 backfill 구별, 이전 결과 보존 |
| R03 식별자 | DB-01/03/06/07/11, ID-01/02 | legacy COSPAR와 내부 UUID 분리, multi-source orbit key |
| R04 호환 | API-01/03/05/12/14/15, ARC-04, DB-05, UX-09 | 기존 반환·inclusive 날짜·sync 보존 계획, raw 미보존 경로의 의미 |
| R05 수집 | EXT-01, HTTP-01~05, ARC-03~07, DB-09, META-04 | per-page raw, completeness·partial·checked_empty, signature·session close |
| R06 소스 | META-01~06, ADM-01~08, SRC-01~13, E2E-06/16 | 사전 평가와 최종 admission 분리, dataset/field/time/rights/evidence matrix |
| R07 과학 | DER-02~17, API-08/09/17, QA-07, E2E-08/14 | backend·입력·기준값·허용오차·실제 pilot window |
| R08 결과·규모 | API-14/16/19, OUT-01~08, PLOT, QA-08 | copy/view·lineage snapshot, batch 및 export pair 완전성 |
| R09 출시 | QA-03/06, REL-01~16, DOI-01~10, DONE-05/06 | 계정/이름·동일 artifact·중간 실패/yank/수정 버전·DOI 대기 처리 |

현재 G0도 미완료다. 9월 30일까지 가용 10~20시간은 복구·회귀·핵심 계약 착수 예산으로 배분하며 전체 출시 보장으로 해석하지 않는다. docs/AI_USAGE는 아직 Git 미추적이고 origin은 placeholder다. 로그인 GitHub 계정의 10개 저장소에서는 orbitoby/space-object-archive 이름을 찾지 못했으며 다른 계정·조직의 존재는 미확인이다. 외부 게시·계정 변경은 수행하지 않았다.


## 23. 최신 일정·역할 / 문서 1.3

사용자는 개발 시간을 늘리고 전체 범위·품질을 유지한 9월 30일 출시를 지정했다. 세부 일정은 ORBITOBY_SEPTEMBER_RELEASE_PLAN.md를 따른다. 22절과 재점검 보고서의 10~20시간 배분은 과거 가정이며 최신 실행 계획에 적용하지 않는다. 기존 250개 ID·완료 체크 7개는 유지한다. 구현·검증·출시 완료 표시는 실제 결과를 받은 후에만 갱신한다. Codex 코드 제공/사용자 실행 방식을 따르며 이번 일정 작성으로 제품 소스·사용자 자료·계정·remote·배포 상태를 변경하지 않았다.

## 24. 2026-09-29 실행 시작 — 코드 전달 01

사용자가 오늘 28·29일 계획을 진행하도록 지시했다. 제품 source 20개는 9/28 snapshot과 동일하다. `docs/handoffs/2026-09-29/README.md`에 복구 스크립트, 합성 테스트 5개, 아키텍처 계약안과 실행 절차를 전달했다. Codex는 Python AST 구문 확인만 수행했고 스크립트·pytest·운영 복구를 실행하지 않았다. 상태는 **사용자 적용/실행 결과 대기**다. 28일 계획의 G0/G1이나 29일 G2를 통과한 것으로 표시하지 않는다. 다음 입력은 합성 테스트, prepare, Space-Track subset reindex 결과이며 이후 전체 raw backfill 및 새 구조 구현으로 이어간다.

### 2026-09-29 검증 기록

사용자가 `.venv/bin/python -B -m pytest -q --tb=short -p no:cacheprovider docs/handoffs/2026-09-29/test_01_archive_recovery.py`를 실행했다. 첫 실행은 3 failed/2 passed였고, DuckDB `TIMESTAMPTZ` Python 변환이 환경에 없는 `pytz`를 요구한 것이 공통 원인이었다. 복구 스크립트의 baseline 조회를 DB 안에서 문자열로 변환하도록 수정한 뒤 사용자가 다시 실행해 **5 passed in 14.40s**를 보고했다. 이는 합성 복구 스크립트 테스트 통과 증거이며 실제 사용자 archive의 backup·path repair·reindex 완료 증거는 아니다.

| ID | 현 상태 | 다음 증거 |
|---|---|---|
| AUD-08 / DB-08 | 합성 백업·복구 코드 테스트 통과, 실제 DB 작업 미실행 | `prepare_summary.json`, 복제본 검증·복원 리허설 |
| AUD-11 / AUD-12 | 합성 NORAD 228·재시작/cache 흐름 테스트 통과, 실제 DB 미검증 | Space-Track subset reindex 보고·기존 17행/coverage 내용 비교 |
| ARC-09 / ARC-10 | 합성 hash 불일치/manifest 불일치 차단 테스트 통과 | 실제 12 artifact hash·manifest 확인, 전체 reindex 결과 |

다음 작업은 사용자 `prepare` 실행 결과 확인이다. 위 ID는 수용 범위 전체가 끝나지 않아 기존 `[ ]`를 유지한다. G0/G1/G2도 미통과다.

### 2026-09-29 실제 archive 준비 결과

사용자가 `01_archive_recovery.py prepare`를 실행해 `status=prepared`, artifacts=12, coverage=2, orbit_elements=17, `production_modified=false`, `backup_verified=true`, `working_paths_repaired=true`, `reindex_executed=false`를 보고했다. Codex도 별도 작업 폴더의 요약·state 파일을 읽기 전용 확인해 artifact 12개, backup/working DB 존재, reindex 미실행을 확인했다. `state.json`의 상세 경로나 raw 내용은 기록·공개하지 않는다.

| ID | 이번에 확인된 부분 | 남은 수용 조건 |
|---|---|---|
| AUD-08 / DB-08 | 일관된 원본 snapshot, 검증된 backup·working 복제본 생성 | 복제 DB 재색인, 기존 데이터 내용·조회·실패 복구, 운영 적용 전 restore 리허설 |
| ARC-09 | raw와 manifest 12개가 DB artifact 대응·hash 검사 통과 | 오류 복구 정책 및 전체 reindex 검증 |
| AUD-11 / AUD-12 | 기존 17행/coverage 2행이 baseline으로 보존됨 | 실제 Space-Track 재색인·offline/cache·재시작 조회 |

다음: 복제본에서 `reindex --source spacetrack --dataset gp_history` 실행. 운영본은 아직 수리하지 않았고 체크박스 250개 중 기존 7개 완료 상태를 유지한다.

### 2026-09-29 Space-Track 복제본 재색인 결과

사용자 실행과 작업 폴더의 `reindex_summary.json`을 확인했다. Space-Track `gp_history` artifact **2개**, 정규화한 행 **17개**, 재실행 중복 없음. 복제본은 objects **1**, identifiers **2**, source_records **17**, object_properties **306**. 기존 coverage 구간의 offline/cache 조회 **2건** 검증. 운영 DB/raw·백업 불변 및 기존 궤도·coverage 내용 보존을 보고했다. 이는 선택한 Space-Track 자료의 검증이다. 전체 12개 artifact의 backfill이나 운영 DB 이행은 아직 수행하지 않았다.

| ID | 확인한 증거 | 남은 조건 |
|---|---|---|
| AUD-11 / AUD-12 | 기존 17행·2개 coverage 구간에서 실제 복제본 재색인·조회·중복 방지 통과 | 정식 repo 회귀 fixture 및 일반 요청 재실행 증거 |
| AUD-08 / DB-08 | 운영 원본·백업 불변, 복제본 경로 수리·부분 backfill 통과 | 나머지 10개 artifact 전체 검증, restore 리허설, 운영 이행 |
| ARC-08~10 | Space-Track 2개 raw 재사용·hash·재시작·캐시 검증 | 전 source 검증, parser version 재정규화 계약·구현 |

다음 전달은 [묶음 실행표](handoffs/2026-09-29/03_CHECKLIST_BATCH.md) 기준으로 여러 ID를 모아 한 번에 실행·보고한다. 현재 완료 체크 수는 **7/250 유지**. 체크가 늦다는 뜻이 아니라 각 ID의 남은 수용 조건을 아직 검증하지 않았다는 뜻이다.

### 2026-09-29 전체 복구 묶음 결과 및 차단

사용자 실행에서 새 합성 테스트 **6 passed in 15.46s**, 백업 복원 리허설 `status=passed`, baseline DB/raw hash 일치·운영본 미변경을 확인했다. 전체 복제본 재색인은 CelesTrak GP 1행, satcat 1행, GCAT psatcat100k 693행까지 완료한 뒤 GCAT `satcat` artifact `20260922T071856Z_effb95676e50`에서 실패했다. 기존 실패 보고서가 artifact ID만 기록해 예외 원문이 없었으므로 원인은 **미확정**이다. GCAT satcat raw 69,999행을 읽기 전용 정규화·JSON 직렬화 검사했으며 그 단계의 오류는 재현되지 않았다. 스크립트가 재색인 오류 문자열을 로컬 보고서에 기록하도록 고쳤고, 해당 dataset만 재실행해 원인을 수집한다. 운영 원본과 백업은 건드리지 않았다. 전체 12개 통과·운영 적용 및 G0/G1/G2 완료는 아니다.

출시 외부 의존: 사용자는 GitHub 저장소를 새로 만들어야 한다고 확인했다. PyPI·TestPyPI·Zenodo 계정 가입은 완료했다. 각 계정의 프로젝트명/소유권, GitHub 연동과 Trusted Publisher 권한은 아직 검증되지 않았다. REL-01/06, DOI-01 완료 표시는 보류한다.

### 2026-09-30 공개 개발 경로 교정

사용자가 Orbitoby의 **공개 개발** 원칙을 재확인했다. 이전 handoff의 private 신규 repo 지시는 잘못된 제안이었다. 신규 저장소는 public로 만들고, 기존 코드/history는 secret scan 및 공개할 파일 검토 후 push한다. 만약 private repo가 이미 만들어졌다면 중복 생성하지 않고 내용 검토 후 그 repo의 visibility를 public로 전환한다. 빈 public repo 생성과 사용자 자료·비밀이 포함될 수 있는 Git history push는 별도 단계다. 이 교정은 공개 repo 존재, secret scan 완료, G0/G1 또는 REL/DOI 완료를 의미하지 않는다.

저장소 표시 이름은 사용자의 선택에 따라 `Orbitoby`, PyPI 배포명과 Python import 이름은 `orbitoby`로 정한다. GitHub description에는 연구 소프트웨어의 대상과 용도를 명시한다. 사용자가 [JIN-ARTLW/Orbitoby](https://github.com/JIN-ARTLW/Orbitoby)를 생성했고 Codex가 `PUBLIC`, 빈 저장소, 요청한 description을 확인했다. 로컬 origin은 아직 placeholder이며 코드 공개 push·GitHub Release는 실행되지 않았다. AUD-14는 최초 코드 공개 증거까지 요구하므로 아직 미완료다.

### 2026-09-30 GCAT 재색인 차단 원인

사용자 작업 폴더의 `reindex_failure.json`을 읽기 전용 확인했다. GCAT `satcat` artifact `20260922T071856Z_effb95676e50`에서 DuckDB가 256 KiB 블록을 pin하지 못했고 6.3 GiB/6.3 GiB 메모리 한계에 도달했다. 실패 후 복제본을 읽기 전용 확인하니 artifacts 12, objects 693, source_records 712, object_properties 19,745로, GCAT `satcat` 행은 commit되지 않았다. 이는 parser·JSON 직렬화 오류가 아니라 쓰기 도중의 메모리 오류다. 복구 리허설 worker에 DuckDB 단일 스레드·입력 순서 보존 해제 설정을 추가했다. 합성 테스트와 GCAT subset 재실행은 사용자 검증 대기이며, 설정만으로 해결됐다고 판단하지 않는다. 전체 재색인과 운영 이행은 여전히 차단된다.
