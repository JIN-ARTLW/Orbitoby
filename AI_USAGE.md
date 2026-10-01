# AI 사용 기록 / AI Usage

AI 도구의 기여, 실제 검증, 사람의 검토와 최종 결정을 구별해 기록한다. / Record AI contributions, performed validation, human review, and final decisions separately.

이 파일은 Master Plan v2.0 §21에 따른 초기 기록이다. 저널 정책 준수 인증이나 실제 사람 검토 완료를 의미하지 않는다. 과거 코드의 기여 이력은 조사 전이다. / This initial record is not a compliance certification or confirmation of human review. Earlier code contributions have not yet been audited.

| 날짜 / Date | 도구·모델 / Tool & model | 기여 범위 / Scope | 수행 검증 / Validation | 사람 검토 / Human review | 최종 결정자 / Decision maker |
|---|---|---|---|---|---|
| 2026-09-28 | Codex; exact model identifier not recorded | Checklist, architecture proposal, existing-code audit, metadata cleanup proposal | 15 isolated synthetic checks; read-only DB counts and raw hashes; syntax/lint evidence in docs/audit/2026-09-28 | Pending substantive document/code review | User; implementation decisions pending |
| 2026-09-28 | Codex; exact model identifier not recorded | Compare supplied Master Plan v2.0 with derived docs; correct omissions/conflicts | Original SHA-256, sections 0–55 mapping, checklist ID/fence validation | Pending | User; source document designated by user |

## 기록 원칙 / Recording rules

- 실제로 수행하지 않은 review/validation은 완료로 표시하지 않는다. / Never mark unperformed review or validation as complete.
- 사용자가 자료를 제공하거나 작업 권한을 허용한 것은 내용 전체를 검토한 것과 다르다. / Providing material or authorizing work is not substantive review.
- 주요 설계 결정 이유는 docs/adr에 별도로 남긴다. / Record significant design rationale in docs/adr.
- 비밀값·계정정보·제한된 데이터는 기록하지 않는다. / Do not record secrets or restricted data.
- 외부 투고 시 요구 disclosure와 최신 정책을 다시 확인한다. / Recheck disclosure requirements when preparing a submission.

## 2026-09-28 / 개발 착수 전 계획 검토

Codex가 현재 소스·운영 DB(read-only)·manifest 경로와 checklist 250개를 대조하고 출시 준비 보고서, ID별 상태, source matrix, 설계 0.3/체크리스트 1.2를 작성했다. 현재 소스의 격리 합성 검증 15개 재통과, parser 재색인/generic fetch 저장 차이 2개 재현, Ruff 19개, pytest 수집 0개를 확인했다. PyPI/Zenodo 공식 문서와 로그인 GitHub 계정의 저장소 목록을 읽기 전용 확인했다. 제품 코드·운영 자료·remote·외부 게시 변경은 없다. 사용자는 가용 시간 10~20시간과 기존 저장소 기억 불확실을 알려주었다. 세부 설계·문서에 대한 사람 검토는 Pending이며 최종 결정자는 사용자다. 증거: docs/ORBITOBY_V0.1.0_READINESS_REVIEW.md 및 docs/audit/2026-09-28/plan_review_*.json.

2026-09-28 후속: 사용자 최신 지시(시간 확대, Codex 코드 제공·사용자 적용/실행, v1.0 지향 구조, 9/30 전체 v0.1.0 PyPI·DOI 목표)를 반영해 3일 역산 계획과 체크리스트 1.3을 작성했다. 구현 소스 20개·마스터 원본 해시 불변 및 250개 ID/7개 완료 체크 유지 확인. 제품 실행·게시 없음. 사람의 세부 계획 검토는 Pending.

2026-09-29: 사용자 직접 실행 방식에 따라 `docs/handoffs/2026-09-29/`에 복제본 복구 코드·합성 테스트 5개·실행 절차·핵심 아키텍처 계약안을 작성했다. AST 구문 분석과 기존 src 20개 해시 불변만 확인했다. 제공 스크립트·테스트는 실행하지 않았으며 결과는 사용자 실행 대기다. 운영 데이터와 제품 소스는 변경하지 않았다. 사람 검토/검증은 Pending.

2026-09-29 후속: 사용자 실행으로 합성 5 tests, 실제 archive prepare, 복제본 Space-Track subset reindex 성공을 확인하고 체크리스트에 증거를 기록했다. 이어서 전체 raw reindex/복원 리허설용 코드·테스트 1개 및 체크리스트 묶음 실행표를 작성했다. 새 6-test suite와 전체 raw·복원 검증은 사용자 실행 전이며 완료 처리하지 않았다. 제품 소스·운영 DB/raw는 변경하지 않았다.

2026-09-30: 사용자가 공개 개발 원칙을 재확인했다. 이전 private GitHub 저장소 안내를 public empty repo 생성으로 정정하고 handoff/체크리스트에 기록했다. Git history 2개 commit, 경로 52개에서 env/DB/raw 추적 경로와 주요 private-key/GitHub/PyPI/AWS token 패턴을 읽기 전용 검사해 탐지된 항목이 없었다. 이는 전수 secret scan 완료 판정이 아니며 코드 push·repo 생성은 실행하지 않았다. GCAT 오류 진단은 사용자 실행 중이다.
