<!-- Current execution evidence: RELEASE_0_1_0_REPORT.md; API contracts: wiki/index.md. -->
# Orbitoby 통합 마스터플랜 / Consolidated master plan

갱신: 2026-10-04 · 상태: 0.1.0 코드 freeze, 로컬 출시 후보 검증 완료, 게시 대기. / Updated: 2026-10-04 · Status: 0.1.0 code frozen, local candidate verified, publication pending.

이 파일이 현재 계획·우선순위·미완료 항목의 단일 기준이다. 사용법은 [문서 색인](index.md), 실제 검증 증거는 [릴리스 보고서](RELEASE_0_1_0_REPORT.md), 재실행 명령은 [릴리스 절차](release.md)에 둔다. 승인이나 검증 없이 미래 목표를 완료로 바꾸지 않는다. / This file is the single authority for current plans, priorities, and unfinished work. See the [guide index](index.md) for usage, the [release report](RELEASE_0_1_0_REPORT.md) for evidence, and [release procedure](release.md) for commands. Future goals require actual approval or evidence before being marked complete.

<a id="decisions"></a>
## 1. 결정 근거와 우선순위 / Decision sources and precedence

최신 사용자 지시 → 메인 2의 최종 합의 → 메인 1의 연구 목표 → 기존 마스터플랜·파생 계획 순으로 충돌을 조정했다. 코드의 존재, 테스트 통과, 과학적 검증, 사용자 검토, 공개 출시는 서로 다른 상태다. 숫자 백분율로 완료도를 표현하지 않는다. / Conflicts are resolved in this order: latest user instructions, final Main 2 decisions, Main 1 research goals, then the earlier master and derived plans. Implementation, passing tests, scientific validation, human review, and public release are separate states. Completion is not expressed as an unsupported percentage.

| 근거 / Source | 반영 / Treatment |
| --- | --- |
| orbitoby 메인 1 (internal planning reference) | 제공된 대화 본문과 기존 계획을 대조. 넓은 LEO 모집단, QC 후 cohort, 물리 메타데이터 완전성 등급, 연구 재현성 유지. 전체 대화 원본을 모두 복원했다는 주장은 하지 않음. / Available conversation text was compared with existing plans. Preserve broad LEO sampling, QC before cohort selection, physical-metadata completeness tiers, and reproducibility. This is not a claim of full original-history recovery. |
| orbitoby 메인 2 (internal planning reference) | 제공되는 과거 페이지를 끝까지 확인. 파일 중심 저장, 명시적 provenance, canonical/window/MSIS/SVG, 최신 freeze, 성능·의존성 개선 연기 반영. / Read all available paginated history. Retain file-first storage, explicit provenance, canonical/window/MSIS/SVG, final freeze, and deferred performance/dependency work. |
| 기존 Master Plan v2, 설계·250항목 체크리스트·복구·일정 문서 / Earlier Master Plan v2, design, 250-item checklist, recovery and schedule documents | 원문 백업 후 아래 목표·위험·요구사항 추적표로 통합. 예전 9/30 일정은 이력이며 현재 마감 약속이 아님. / Originals are backed up and consolidated into goals, risks, and traceability below. The former September 30 target is historical, not a renewed deadline. |
| 2026-10-01 대화상의 baseline/TODO 첨부 링크 / Baseline/TODO attachment links mentioned on 2026-10-01 | 대화에 보이는 결정만 반영. 회수되지 않은 별도 첨부 파일의 본문까지 읽었다고 하지 않음. / Incorporate visible decisions only; do not claim to have read unrecovered attachment contents. |

<a id="scope"></a>
## 2. 제품과 연구의 범위 / Product and research scope

**Orbitoby**는 범용 자료 수집·정규화·저장·조회·모델 실행·출처 추적 패키지다. **2026 사이언스 데이 연구**는 별도 연구 저장소에서 태양 활동 → 열권 밀도 → 항력 → 궤도 감소 가설을 분석한다. 특정 연구의 cohort, 통계 모형, 그림, 결론을 범용 core에 숨겨 넣지 않는다. / **Orbitoby** is a general-purpose acquisition, normalization, storage, query, model-execution, and provenance package. The **2026 Science Day study** belongs in a separate research repository and investigates solar activity → thermospheric density → drag → orbital decay. Study-specific cohorts, statistical models, figures, and conclusions do not become hidden core behavior.

0.1.0에서는 기능·성능 코드를 동결한다. 문서, 재현 가능한 패키징, 확인된 출시 결함의 최소 수정만 범위다. 추가 provider discovery cache, 추가 병렬화, 새 제품·CLI·범용 derive/export/cohort는 이번에 구현하지 않는다. / Version 0.1.0 freezes functionality and performance. Scope is documentation, reproducible packaging, and minimum corrections for demonstrated release defects. Additional provider-discovery caching, further concurrency, new products, CLI, and general derive/export/cohort features are not implemented in this pass.

<a id="state"></a>
## 3. 현재 상태와 근거 / Current state and evidence

| 항목 / Area | 현재 사실 / Current fact | 한계·후속 / Limit or follow-up |
| --- | --- | --- |
| Catalogue | 깨끗한 Archive에서 15 providers / 103 curated datasets 검증. / Verified 15 providers and 103 curated datasets in a clean Archive. | 등록 수는 모든 live 경로의 안정성 인증이 아님. / Registration counts do not certify every live path. |
| Acquisition/canonical | 지원 제품의 raw→canonical 저장·재조회·provenance·실패 정리 테스트 통과. / Supported raw→canonical storage, cache, provenance and failure cleanup tests pass. | 모든 provider가 모든 canonical 제품을 지원한다는 뜻은 아님. / Not every provider supports every canonical product. |
| Timeseries/window | UTC, 명시적 변수·객체, 정확한 timestamp 정렬과 결측성 보존. / UTC, explicit variable/object selection, exact timestamp alignment and preserved missingness. | 자동 보간·채움·상충 자료 병합 없음. / No silent interpolation, fill or conflict merge. |
| MSIS | 선택 extra의 pymsis 0.13.0, 명시적 입력 실행 및 제품 provenance 검증. / Optional pymsis 0.13.0 execution and product provenance verified with explicit inputs. | 관측 밀도·자동 궤도 전파·decay 추정과 구별. / Distinct from observed density, automatic orbit propagation or decay estimation. |
| Plotting | 추가 plotting 의존성 없는 SVG 시계열 지원. / Native SVG timeseries support without a plotting dependency. | 다중 패널·고급 export·통계 그림은 이후 범위. / Advanced panels, exports and statistical figures remain future work. |
| Discovery performance | 필터 적용, metadata 별도 timeout/retry, 제한된 provider 병렬 처리, Archive 수명 내 TTL/negative cache와 연결 차단 정책이 현재 코드에 있음. / Current code includes filtering, separate metadata timeout/retry, bounded provider concurrency, per-Archive TTL/negative cache and connection-breaker policy. | 과거 체감 속도를 이번 재측정 결과로 제시하지 않음. persistent/batch 확장은 보류. / Earlier latency impressions are not new benchmarks; persistent/batch extensions are deferred. |
| Objects/plugins | objects는 수집된 로컬 catalog 조회. 플러그인 신뢰와 canonical mapping은 명시적. / objects queries the ingested local catalog; plugin trust and canonical mapping are explicit. | 자동 객체 다운로드·이름만으로 동일 객체 병합·플러그인 sandbox를 약속하지 않음. / No implicit object download, name-only identity merge or plugin sandbox guarantee. |
| Verification | Python 3.12 전체 249 tests, 3.12/3.13/3.14 fresh base/models smoke, strict Twine 통과 기록. / Recorded 249 full-suite tests on Python 3.12, fresh base/models smoke on 3.12/3.13/3.14, and strict Twine validation. | 버전별 전체 suite·모든 OS·Colab·전 provider live 검증은 아님. / Not full suites on every version, all OS/Colab, or every live provider. |

정확한 새 artifact 경로·해시와 문서 갱신 이후 재검증은 [릴리스 보고서](RELEASE_0_1_0_REPORT.md)를 기준으로 한다. / The [release report](RELEASE_0_1_0_REPORT.md) is authoritative for new artifact paths, hashes, and post-documentation verification.

<a id="contracts"></a>
## 4. 보존할 설계·과학 계약 / Design and scientific contracts

- **자료를 추측하지 않는다.** 지원 여부, 시간 coverage, 단위, 프레임, 객체, 결측, provisional/revised 상태를 모르면 모른다고 남긴다. / **Never guess data.** Unknown support, temporal coverage, units, frames, identity, missingness, and provisional/revised status remain unknown.
- Canonical 시계열과 window는 UTC의 `[start, end)`이다. 현재 `orbit()`도 날짜 기반 `[start,end)`이며 종료일을 제외한다. / Canonical timeseries and windows use UTC `[start, end)`. Current `orbit()` also uses date-based `[start,end)`, excluding the end date.
- Source-native 측정·모델·파생 값은 구별한다. NRCan 관측/보정/1 AU 값, Swarm ACC/POD 등 다른 제품을 암묵적으로 합치지 않는다. / Distinguish native measurements, model outputs and derived values. Do not silently combine NRCan observed/adjusted/1 AU values or Swarm ACC/POD products.
- Raw와 큰 과학 배열은 파일, DuckDB는 metadata/index 중심으로 유지한다. 원본 checksum, 요청 범위, 취득 시점, dataset/provider, parser/모델 맥락, 부모 artifact의 추적성을 유지하고 secret은 기록하지 않는다. / Keep raw payloads and large scientific arrays in files, with DuckDB focused on metadata/indexes. Preserve checksums, request bounds, acquisition times, dataset/provider, parser/model context and parent-artifact lineage without secrets.
- 현재 Archive 생성자는 DB를 연다. 계획상의 lazy constructor·Settings 인수·typed FetchSpec/RawPage/NormalizedBatch/AcquisitionResult를 이미 제공되는 API로 쓰지 않는다. / The current Archive constructor opens the DB. Planned lazy construction, Settings arguments and typed FetchSpec/RawPage/NormalizedBatch/AcquisitionResult must not be documented as existing APIs.
- 실패한 canonical/product DB 등록 뒤 파일 정리 테스트는 통과했다. raw payload와 manifest 두 파일의 crash-atomic transaction까지 증명한 것은 아니다. schema migration, parser-version replay, crash recovery는 별도 설계·검증이 필요하다. / Canonical/product cleanup after failed DB registration is tested. This does not prove a crash-atomic transaction for the raw payload/manifest pair. Schema migration, parser-version replay and crash recovery require separate design and validation.
- 인증 우선순위는 runtime→keyring→environment→Colab→명시적 dotenv이며 `.env`는 opt-in이다. settings permission 0600을 유지한다. 신뢰한 플러그인 코드는 실행 권한을 가지므로 사용자 검토가 필요하다. / Credential resolution is runtime→keyring→environment→Colab→explicit dotenv; `.env` is opt-in. Preserve mode 0600 settings. Trusted plugin code executes with process privileges and needs review.
- 객체 식별은 검증 가능한 NORAD/COSPAR/원천 cross-ID를 사용하고 충돌과 유효 시점을 보존한다. 이름만으로 합치지 않는다. 결측 mass/area/Cd를 core가 채우지 않으며 B*를 곧바로 물리 ballistic coefficient로 취급하지 않는다. / Use verifiable NORAD/COSPAR/source cross-IDs and preserve conflicts and validity times. Never merge by name alone, infer missing mass/area/Cd, or equate B* directly with a physical ballistic coefficient.
- Provider 변경은 endpoint/profile/adapter/parser 경계에서 해결하는 것이 방향이다. core를 매번 재설계하거나 upstream 실패를 자료 없음으로 숨기지 않는다. / Handle provider changes at endpoint/profile/adapter/parser boundaries. Avoid redesigning the core for each change or disguising upstream failure as absent data.
- Source lifecycle은 candidate→experimental→stable, 필요에 따라 restricted/deprecated/removed로 관리하는 장기 정책이다. official endpoint, 이용권한·rate limit, auth, schema/units/quality, fixture/live evidence, citation을 개별 확인한다. curated 등록만으로 stable을 선언하지 않는다. / The long-term source lifecycle is candidate→experimental→stable, with restricted/deprecated/removed as needed. Review official endpoints, rights/rate limits, auth, schema/units/quality, fixtures/live evidence and citations individually; curated registration alone is not stable status.

<a id="release"></a>
## 5. 0.1.0 출시 게이트 / Release gates

| 구분 / Gate | 상태와 조치 / Status and action |
| --- | --- |
| 로컬 기술 검증 / Local technical verification | 기존 전체 249 tests 및 wheel matrix 통과. 이번 문서/NOTICE 변경으로 artifact를 재생성하고 결과를 보고서에 기록한다. / Earlier full 249-test run and wheel matrix passed. Rebuild after these README/NOTICE changes and record results in the report. |
| 공개 파일·링크 / Published files and links | **미완료 blocker.** 직전 banner/guide 공개 URL은 404. 검토한 코드·문서·배너와 기존 untracked 구현을 출시 commit에 포함하고 실제 URL을 재확인해야 한다. / **Open blocker.** Banner/guide URLs returned 404 in the prior audit. The release commit must preserve reviewed code/docs/banner and pre-existing untracked implementation, then verify actual public URLs. |
| 업로드 승인 / Upload authorization | **대기.** 사용자의 명시적 승인 전 PyPI upload 금지. 같은 0.1.0 이름의 stale TestPyPI 파일에 의존하지 않는다. / **Pending.** No PyPI upload before explicit user approval; do not rely on stale TestPyPI 0.1.0 files. |
| 사람 검토 / Human review | 이 문서 생성·실행 권한은 내용 전체 검토 완료와 다르다. 변경 diff와 최종 artifact를 검토할 수 있게 보존한다. / Authorization to write/run is not completed substantive review. Preserve the diff and exact artifacts for review. |
| DOI·Pages / DOI and Pages | 후속 작업. DOI를 만들지 않았고 Pages도 활성화하지 않았다. 최신 합의상 DOI는 0.1.0 build blocker가 아니다. / Follow-up work. No DOI or Pages activation is claimed. Under the latest decision, DOI is not a 0.1.0 build blocker. |

새 기능·속도 개선은 출시 blocker가 아니다. 반대로 검증 중 재현된 자료 손상·잘못된 과학 값·secret 유출·설치 실패는 숨기지 말고 범위가 작은 수정과 관련 재검증으로 처리한다. / New features and performance improvements are not release blockers. Reproduced corruption, incorrect scientific values, exposed secrets or installation failures require a narrow correction and relevant revalidation.

<a id="roadmap"></a>
## 6. 0.1.0 이후 제품 로드맵 / Post-0.1.0 product roadmap

모든 행은 계획이며 구현 승인이 아니다. 우선순위는 근거 수집 후 조정하며 출시 날짜·속도·지원 수를 약속하지 않는다. / Every row is a plan, not implementation authorization. Adjust priorities with evidence; do not promise dates, latency or support counts.

| ID | 작업 / Work | 완료 판단 / Acceptance evidence |
| --- | --- | --- |
| P01 | Persistent metadata cache | 유효기간·negative cache·schema/version·invalidation·동시 접근·손상 복구를 정의하고 재시작 전후 결과 일관성을 검증. / Specify TTL, negative entries, schema/version, invalidation, concurrency and corruption recovery; verify consistency across restarts. |
| P02 | 추가 live-discovery 성능 개선 / Further live-discovery performance | cold/warm·실패·필터별 측정, bounded 시간/메모리, unknown coverage 보존. / Measure cold/warm, failure and filtered cases with bounded time/memory and preserved unknown coverage. |
| P03 | Provider-level batch/parallel metadata fetch | provider rate limit·실패 격리·순서·취소·retry 폭주 방지 검증. 과학 데이터 fetch는 별도 검토. / Validate provider limits, failure isolation, order, cancellation and retry amplification; scientific fetch needs separate review. |
| P04 | Curated catalogue 확대 / Expanded curated coverage | source admission, 제품 구별, 단위·quality·provenance·fixture 및 최소 live 확인. / Source admission, product distinctions, units, quality, provenance, fixtures and a bounded live check. |
| P05 | 풍부한 문서·예제 / Richer docs and examples | 재현 가능한 offline/real 예제, notebook·FAQ·연구 workflow, 버전별 API 일치. / Reproducible offline/real examples, notebooks, FAQ and study workflows matching versioned APIs. |
| P06 | Advanced plotting/export | 단위/축/결측/QC 표시, 명시적 aggregation, 재현 가능한 결과와 provenance sidecar 설계. / Explicit units, axes, missingness/QC, aggregation, reproducible output and provenance-sidecar design. |
| P07 | Additional derived/model products | 입력·물리 가정·단위·frame·불확실성·부모 artifact·reference validation을 먼저 정의. / Define inputs, physical assumptions, units, frames, uncertainty, parent artifacts and reference validation first. |
| P08 | Models extra와 의존성 재검토 / Revisit models extra and dependencies | 0.1.0의 `orbitoby[models]` 유지 후 플랫폼별 wheel/optional boundary 점검. hard dependency 2–3개는 지향점이며 정확성보다 우선하지 않음. pyarrow/dotenv/pytz 역할과 requests 안정성, pymsis 분리를 근거로 검토. / Keep `orbitoby[models]` for 0.1.0, then examine platform wheels and optional boundaries. Two or three hard dependencies are an aspiration, subordinate to correctness; review pyarrow/dotenv/pytz roles, requests stability and pymsis separation using evidence. |
| P09 | Schema migration·raw crash safety·parser replay | 사용자 archive 복제본과 rollback/restore 증거, parser version을 구분한 재처리, 기존 데이터 불변·중복 방지. / Copied user archives with rollback/restore evidence, parser-version-aware replay, preserved data and deduplication. |
| P10 | Generic derive/export/result 계약과 필요 시 CLI / Generic derive/export/result contracts and a CLI if justified | 현재 API와 호환 경계·파일 규모·immutable 결과·sidecar 설계. 제거된 CLI entrypoint를 문서만으로 부활시키지 않음. / Define compatibility boundaries, file scaling, immutable results and sidecars. Do not resurrect a removed CLI entrypoint only in documentation. |
| P11 | CI·보안·운영 환경 확대 / Broader CI, security and environment coverage | 실제 CI, 의존성 감사·정적 보안 검사, cross-OS/Colab, 공개 repo 유지관리·지원 정책의 실증. / Actual CI, dependency/static-security audits, cross-OS/Colab evidence and public maintenance/support policy. |
| P12 | Source admission·identity·coverage 보고 / Source admission, identity and coverage reporting | 성공/완전성/coverage 분리, conflict 이력, source 상태와 권리·citation 명시, temporal/API 호환 정책. / Separate success/completeness/coverage, preserve conflict history, disclose source status/rights/citation and temporal/API compatibility policy. |

<a id="research"></a>
## 7. 연구 트랙 / Research track

### 모집단과 cohort / Population and cohorts

소수의 임의 위성부터 고르는 대신 LEO 후보를 폭넓게 모으고, 객체 정체성·궤도 품질·시계열 coverage·기동·재진입·메타데이터 충돌을 검사한 뒤 분석 cohort를 만든다. Payload/rocket body/debris 및 active/inactive 구분을 보존하고 제외 이유를 기록한다. 객체 수 자체가 성공 기준은 아니다. / Start from a broad LEO candidate population, then assess identity, orbital quality, time coverage, maneuvers, reentry and metadata conflicts before defining analysis cohorts. Preserve payload/rocket-body/debris and active/inactive distinctions and record exclusions. Object count alone is not success.

A: 물리 메타데이터가 충분한 주분석, B: 궤도는 충분하지만 mass/area 등이 부족한 확장·민감도 분석, C: 보조 비교 등급을 사전에 정의한다. 결측 mass/area 때문에 전체를 자동 폐기하거나 값을 추정해 넣지 않는다. 최소 GP 수·최대 gap·epoch/고도 범위·기동 flag 기준은 연구 config에 명시하고 민감도 분석한다. / Define tiers in advance: A for sufficiently complete physical metadata, B for sufficient orbits with missing mass/area or related attributes, and C for auxiliary comparisons. Do not automatically discard all incomplete objects or invent missing values. Specify minimum GP count, maximum gap, epoch/altitude bounds and maneuver flags in study configuration and test sensitivity.

### 질문·방법 / Questions and methods

| 연구 질문 / Research question | 필요한 근거 / Required evidence |
| --- | --- |
| RQ1 태양 활동과 궤도 감소 / Solar activity and orbital decay | 재현 가능한 궤도 감소 정의, 시간 정렬과 lag 가정. / Reproducible decay definition, time alignment and lag assumptions. |
| RQ2 지자기 활동의 추가 설명력 / Added geomagnetic explanatory value | 태양 지표와 공선성·자기상관·다중 비교 고려. / Account for collinearity with solar indices, autocorrelation and multiple comparisons. |
| RQ3 태양 활동→밀도 / Solar activity→density | 관측 밀도와 MSIS 출력 구별, forcing 출처·시간 인과성 검토. / Distinguish observed density from MSIS and review forcing provenance and temporal causality. |
| RQ4 밀도→궤도 감소 / Density→decay | 고도·mass/area/Cd·기동 영향과 불확실성. / Altitude, mass/area/Cd, maneuver effects and uncertainty. |
| RQ5 고도 의존성 / Altitude dependence | 고도 bin 선택·표본 불균형·시간별 고도 변화 민감도. / Sensitivity to altitude bins, sample imbalance and evolving altitude. |
| RQ6 물리 속성 의존성 / Physical-property dependence | A/B/C 완전성 등급과 선택 편향·메타데이터 충돌. / Completeness tiers, selection bias and metadata conflicts. |
| RQ7 태양 주기별 견고성 / Robustness across solar cycles | 시간·객체 holdout, cycle별 coverage와 같은 preprocessing. / Temporal/object holdouts, cycle coverage and consistent preprocessing. |

TLE/GP는 정밀한 순간 관측 궤도와 같지 않다. pointwise 차이, window slope, 집계 변화량을 비교하고 estimator·window·QC·reference frame을 명시한다. 자료 진단 후 회귀/계층 모형 등을 결정하며 자기상관, lag 탐색, 이분산, 공선성, 불균형 표본, 반복 객체 관측을 고려한다. 상관관계만으로 인과·매개 효과를 확정하지 않는다. / TLE/GP is not a precision instantaneous orbit observation. Compare pointwise differences, window slopes and aggregated changes with explicit estimators, windows, QC and reference frames. Choose regression/hierarchical methods after diagnostics, accounting for autocorrelation, lag search, heteroskedasticity, collinearity, imbalanced samples and repeated objects. Correlation alone does not establish causality or mediation.

단계는 baseline 재현 → 밀도 매개 가설 → 객체/물리속성 민감도 → 시간·주기 견고성 → 모델 reference 검증이다. 연구 저장소에 config·환경·package version/commit·입력 manifest/checksum·CITATIONS/LICENSES·표/그림 생성 경로를 기록한다. 제한 자료는 재배포 권리를 확인하고 acquisition recipe로 대체할 수 있다. / Stages are baseline reproduction, density-mediation hypotheses, object/physical-property sensitivity, temporal/cycle robustness, and model-reference validation. Record configs, environments, package version/commit, input manifests/checksums, CITATIONS/LICENSES and table/figure-generation paths in the study repository. Check redistribution rights for restricted data and use acquisition recipes when needed.

<a id="maturity"></a>
## 8. v1.0·재현성·학술 목표 / v1.0, reproducibility and scholarly goals

| Gate | 장기 완료 기준 / Long-term completion criterion |
| --- | --- |
| A 소프트웨어 / Software | 문서화된 안정 API, tested storage/migration, source admission, 실제 배포와 유지관리. / Documented stable APIs, tested storage/migration, source admission, real distribution and maintenance. |
| B 연구 / Research | 사전 정의한 cohort/QC와 통계 진단, reference 비교, 재현 가능한 표·그림·해석. / Predefined cohorts/QC, statistical diagnostics, reference comparisons and reproducible tables, figures and interpretation. |
| C 재현 / Reproduction | 새 환경의 end-to-end 재실행, 버전·입력·출처·라이선스 고정, 독립 검토. / End-to-end reruns in a clean environment, pinned versions/inputs/provenance/licenses and independent review. |
| D 학술 / Scholarly | 실제 release에 대응하는 citation/필요 시 Zenodo DOI, AI 기여 공개, 투고 당시 저널 정책 확인. / Citation and, when appropriate, a Zenodo DOI corresponding to the real release, AI disclosure and current journal-policy review at submission. |
| E 성숙도 / Maturity | 호환성·deprecation·보안 대응·기여 절차와 실제 사용자 피드백, v1.0 기준 재검토. / Compatibility, deprecation, security response, contributions, real user feedback and reviewed v1.0 criteria. |

JOSS/SoftwareX 등은 후속 검토 후보이지 수락·적격성이 확인된 상태가 아니다. 과거 개발기간 조건이나 일정은 최신 공식 정책 확인 없이 확정 규칙으로 재사용하지 않는다. DOI는 검증된 값만 기록하고 release/tag/archive의 대응을 유지한다. / JOSS/SoftwareX are future submission options, not confirmed eligibility or acceptance. Do not reuse historic development-duration rules or deadlines without checking current official policies. Record only verified DOIs and preserve correspondence among release, tag and archive.

<a id="risks"></a>
## 9. 미해결 설계·위험 등록부 / Open design and risk register

| ID | 보존할 쟁점 / Preserved issue | 처리 / Treatment |
| --- | --- | --- |
| R01 | 백업과 schema migration은 다름. / Backup is not schema migration. | 복제본 rehearsal·restore·버전별 변환 증거 필요. / Require copied-archive rehearsal, restore and versioned transformation evidence. |
| R02 | Reindex/backfill과 parser replay는 다름. / Reindex/backfill is not parser replay. | parser version과 acquisition run 이력을 보존하는 재처리 설계. / Design replay with parser versions and acquisition-run history. |
| R03 | Legacy COSPAR object_id와 향후 UUID identity 경계. / Legacy COSPAR object_id versus future UUID identity. | cross-ID/충돌/이행 정책을 별도 검토, 자동 변경 금지. / Review cross-ID, conflict and migration policy separately; no automatic rewrite. |
| R04 | API·시간 구간 호환성. / API and temporal-bound compatibility. | 현재 orbit와 canonical의 half-open 규칙 명시. / Document current half-open orbit and canonical intervals. |
| R05 | 성공·완전성·coverage 의미가 다름. / Success, completeness and coverage differ. | 미지원·unknown·partial·upstream failure를 숨기지 않는 보고. / Report unsupported, unknown, partial and upstream-failure states explicitly. |
| R06 | Source 사전 admission과 기술적 작동은 다름. / Source admission differs from technical operation. | 권리·공식성·quality·지원 상태까지 검토. / Review rights, official status, quality and support state. |
| R07 | MSIS backend smoke와 과학 reference 검증은 다름. / MSIS smoke differs from scientific reference validation. | reference 수치·단위·forcing·look-ahead 방지·불확실성 검토. / Validate reference values, units, forcing, look-ahead avoidance and uncertainty. |
| R08 | 대용량 immutable result와 export sidecar 설계. / Large immutable results and export sidecars. | 확장성과 provenance를 보존하는 공개 계약 검토. / Review public contracts preserving scalability and provenance. |
| R09 | Git/PyPI/DOI artifact 동일성. / Git/PyPI/DOI artifact correspondence. | 검토된 commit과 정확한 해시, 게시 후 파일 대체 금지. / Reviewed commit and exact hashes; never replace published files. |
| R10 | API 중단·rate limit·권리·secret·악성 plugin. / API outages, rate limits, rights, secrets and malicious plugins. | bounded 요청, 권한 검토, 비밀값 제외, 신뢰의 명시성. / Bounded requests, permission review, excluded secrets and explicit trust. |
| R11 | 연구 scope 혼입·통계 과해석·AI 검토 공백. / Study leakage, statistical overinterpretation and unreviewed AI work. | 연구 저장소 분리, sensitivity/holdout, AI_USAGE와 사람 검토 추적. / Separate study repo, sensitivity/holdouts, AI_USAGE and tracked human review. |

<a id="traceability"></a>
## 10. 기존 문서 통합·추적 / Consolidation and traceability

수정 전 31개 문서의 원문 ZIP과 SHA-256 manifest를 로컬 `dist/documentation-backup-20261003/`에 보존한다. 법적 LICENSE 원문, 역사적 증거 JSON, 복구 스크립트·테스트, 배너는 이번 번역 작업으로 수정하지 않는다. 백업은 이력이며 현재 지침이 아니다. / Preserve the 31 pre-edit documents in a local original ZIP and SHA-256 manifest under `dist/documentation-backup-20261003/`. This translation does not modify the legal LICENSE, historical evidence JSON, recovery scripts/tests or banner. Backups are history, not current instructions.

| 이전 문서 / Previous document | 통합 위치 / Consolidated destination |
| --- | --- |
| ORBITOBY_MASTER_PLAN.md, ORBITOBY_MASTER_PLAN_RECONCILIATION.md | 이 문서 전체, 결정 우선순위와 추적표 / This document, precedence and traceability |
| ORBITOBY_ARCHITECTURE_V0.1.0.md, handoffs/2026-09-29/02_ARCHITECTURE_CONTRACTS.md | §4 계약, §6 미래 계약, §9 위험 / §4 contracts, §6 future contracts, §9 risks |
| ORBITOBY_V0.1.0_CHECKLIST.md, handoffs/2026-09-29/03_CHECKLIST_BATCH.md | §5 실제 게이트, 아래 250-ID 매핑 / §5 actual gates and the 250-ID map below |
| ORBITOBY_CURRENT_STATE_AND_CLEANUP.md, ORBITOBY_V0.1.0_READINESS_REVIEW.md | §3 현재 상태, §9 위험, 최신 release report / §3 current state, §9 risks and current release report |
| ORBITOBY_SEPTEMBER_RELEASE_PLAN.md, handoffs/2026-09-30/CHAT_HANDOFF.md | §1 역사적 일정, §5 현재 게이트 / §1 historical schedule and §5 current gates |
| POST_0_1_0_TODO.md | §6 로드맵과 §7–8 연구·성숙도 / §6 roadmap and §7–8 research/maturity |
| handoffs/2026-09-29/README.md, 04_GCAT_FAILURE_DIAGNOSIS.md | 역사적 복구/진단 맥락을 별도로 유지, 현재 상태는 §3·§9 / Retain historical recovery/diagnosis context separately; current status is §3/§9 |
| adr/2026-10-02-native-svg-plotting.md | 결정 근거는 ADR 유지, 현재 범위 §3·§6 / Keep decision rationale in ADR; current scope is §3/§6 |

v2의 0–55절은 문장 단위 번역본 대신 목적별로 통합했다: 제품/연구 목적·원칙 → §1–2; source·identity·auth·HTTP·storage·API·출력 계약 → §3–4·9; QA·릴리스·문서·기여 → §5와 linked guides; 성능·확장·미구현 계약 → §6; 모집단·QC·가설·분석·그림 → §7; 재현성·DOI·논문·v1.0 → §8; 계획 간 충돌 → §1·9–10. 원문 세부는 백업에 보존한다. / Sections 0–55 of v2 are consolidated by purpose rather than translated line by line: product/research goals and principles → §1–2; source, identity, auth, HTTP, storage, API and output contracts → §3–4/9; QA, release, docs and contributions → §5 and linked guides; performance, extensions and unimplemented contracts → §6; population, QC, hypotheses, analysis and figures → §7; reproduction, DOI, papers and v1.0 → §8; conflicting plans → §1/9–10. Original detail remains in the backup.

### 250개 기존 체크리스트 ID / The 250 legacy checklist IDs

아래는 모든 기존 ID의 추적 범위이지 일괄 통과 선언이 아니다. 이전 체크표의 완료 표시 7개도 역사적 증거로만 보존한다. 현재 확인된 부분은 release report를 따르고 나머지는 계약/로드맵/연구 게이트로 계속 추적한다. / This is traceability for every legacy ID, not a blanket pass declaration. The seven previously checked entries are retained only as historical evidence. Currently verified subsets follow the release report; remaining requirements stay in contracts, roadmap or research gates.

| ID 전체 / All IDs | 영역 / Area | 현재 처리 / Current treatment |
| --- | --- | --- |
| AUD-01, AUD-02, AUD-03, AUD-04, AUD-05, AUD-06, AUD-07, AUD-08, AUD-09, AUD-10, AUD-11, AUD-12, AUD-13, AUD-14 | 기존 audit / Historical audit | 역사적 evidence 보존; 현재 상태는 §3·보고서 / Preserve historical evidence; current status is §3/report |
| GOV-01, GOV-02, GOV-03, GOV-04, GOV-05, GOV-06, GOV-07, GOV-08, GOV-09, GOV-10 | 거버넌스 / Governance | freeze·공개 원칙 유지, 사람 검토 대기 / Preserve freeze/public-development principles; human review pending |
| META-01, META-02, META-03, META-04, META-05, META-06, META-07 | 패키지 metadata / Package metadata | 검증된 metadata는 보고서, citation/DOI 후속 / Verified metadata in report; citation/DOI follow-up |
| HTTP-01, HTTP-02, HTTP-03, HTTP-04, HTTP-05, HTTP-06, HTTP-07, HTTP-08, HTTP-09, HTTP-10, HTTP-11 | HTTP | 현재 tests 통과 범위와 P02–03·R10 / Current tested scope plus P02–03/R10 |
| AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07 | 인증 / Authentication | 현재 resolution/permission 확인; 포괄 보안 인증 아님 / Resolution/permissions checked; not comprehensive security certification |
| EXT-01, EXT-02, EXT-03, EXT-04, EXT-05, EXT-06, EXT-07, EXT-08, EXT-09, EXT-10, EXT-11, EXT-12, EXT-13, EXT-14 | 확장 / Extensions | 현재 plugin 계약과 P10–12 / Current plugin contracts and P10–12 |
| ARC-01, ARC-02, ARC-03, ARC-04, ARC-05, ARC-06, ARC-07, ARC-08, ARC-09, ARC-10, ARC-11 | Archive | 현재 생성·조회 계약, 미래 API는 P09–10 / Current construction/query contracts; future APIs P09–10 |
| DB-01, DB-02, DB-03, DB-04, DB-05, DB-06, DB-07, DB-08, DB-09, DB-10, DB-11, DB-12 | 저장 / Storage | 검증된 rollback; migration/raw crash safety는 P09·R01–02 / Tested rollback; migration/raw crash safety P09/R01–02 |
| ID-01, ID-02, ID-03, ID-04, ID-05, ID-06, ID-07 | 객체 식별 / Identity | 기존 식별 보존; R03·P12 / Preserve current identity; R03/P12 |
| ADM-01, ADM-02, ADM-03, ADM-04, ADM-05, ADM-06, ADM-07, ADM-08 | Source admission | 개별 검토 정책, P04·P12·R06 / Individual review policy; P04/P12/R06 |
| SRC-01, SRC-02, SRC-03, SRC-04, SRC-05, SRC-06, SRC-07, SRC-08, SRC-09, SRC-10, SRC-11, SRC-12, SRC-13 | Providers | 15/103 catalogue와 제한 live evidence; 전수 안정성 미확인 / 15/103 catalogue and bounded live evidence; not universal stability |
| API-01, API-02, API-03, API-04, API-05, API-06, API-07, API-08, API-09, API-10, API-11, API-12, API-13, API-14, API-15, API-16, API-17, API-18, API-19 | 공개 API / Public API | 현재 signature 기반 docs; 미구현 계약 P10 / Docs follow current signatures; unimplemented contracts P10 |
| DER-01, DER-02, DER-03, DER-04, DER-05, DER-06, DER-07, DER-08, DER-09, DER-10, DER-11, DER-12, DER-13, DER-14, DER-15, DER-16, DER-17 | 파생·모델 / Derived/model | MSIS 구현 부분과 P07·R07·연구 §7 / Implemented MSIS subset, P07/R07/research §7 |
| OUT-01, OUT-02, OUT-03, OUT-04, OUT-05, OUT-06, OUT-07, OUT-08 | 출력 / Output | 현재 제품 provenance; generic export P06·P10·R08 / Current product provenance; generic export P06/P10/R08 |
| PLOT-01, PLOT-02, PLOT-03, PLOT-04, PLOT-05, PLOT-06, PLOT-07, PLOT-08 | 그림 / Plotting | SVG 범위 검증; advanced P06 / SVG scope verified; advanced work P06 |
| UX-01, UX-02, UX-03, UX-04, UX-05, UX-06, UX-07, UX-08, UX-09 | 사용성 / Usability | 현재 Python API; CLI/환경 확장 P10–11 / Current Python APIs; CLI/environment extensions P10–11 |
| DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06, DOC-07, DOC-08, DOC-09, DOC-10, DOC-11, DOC-12, DOC-13 | 문서 / Documentation | 현재 한/영 통합; 확장 예제 P05 / Current bilingual consolidation; richer examples P05 |
| QA-01, QA-02, QA-03, QA-04, QA-05, QA-06, QA-07, QA-08, QA-09, QA-10, QA-11, QA-12, QA-13 | 품질 / Quality | 실제 suite·smoke 보고서; CI/OS/Colab P11 / Actual suite/smoke report; CI/OS/Colab P11 |
| E2E-01, E2E-02, E2E-03, E2E-04, E2E-05, E2E-06, E2E-07, E2E-08, E2E-09, E2E-10, E2E-11, E2E-12, E2E-13, E2E-14, E2E-15, E2E-16 | End-to-end | 검증된 대표 경로만; 연구 재현은 §7–8 / Verified representative paths only; study reproduction §7–8 |
| REL-01, REL-02, REL-03, REL-04, REL-05, REL-06, REL-07, REL-08, REL-09, REL-10, REL-11, REL-12, REL-13, REL-14, REL-15, REL-16 | 릴리스 / Release | 로컬 검증/공개 링크/업로드 승인 분리 §5 / Separate local verification, public links and upload authorization §5 |
| DOI-01, DOI-02, DOI-03, DOI-04, DOI-05, DOI-06, DOI-07, DOI-08, DOI-09, DOI-10 | DOI | 미완료 후속 §8, 0.1.0 build blocker 아님 / Open follow-up §8, not a 0.1.0 build blocker |
| DONE-01, DONE-02, DONE-03, DONE-04, DONE-05, DONE-06, DONE-07 | 종료 기준 / Completion criteria | 제품·연구·학술 gates를 분리, 일괄 완료 금지 / Separate product/research/scholarly gates; no blanket completion |

총 250개 ID를 중복 없이 매핑했다. 원래 개별 문구와 체크 상태는 원문 ZIP에 보존되어 비교할 수 있다. / All 250 IDs are mapped once. Original wording and checkbox states remain available in the original ZIP for comparison.
