# AI 사용 기록 / AI usage record

AI 기여, 실제 검증, 사람 검토, 최종 결정을 구별한다. 작업 허용이나 자료 제공은 내용 전체의 사람 검토 완료가 아니다. 정확한 모델 식별자는 기록되지 않았으며 추정하지 않는다. / Distinguish AI contribution, performed validation, human review and final decisions. Task authorization or supplied material is not completed substantive human review. Exact model identifiers were not recorded and are not inferred.

| 날짜 / Date | 도구 / Tool | 기여·검증 이력 / Contribution and validation history | 사람 검토 / Human review |
| --- | --- | --- | --- |
| 2026-09-28 | Codex | 초기 계획·설계·metadata 검토, 15개 격리 합성 checks, read-only DB/hash, 당시 Ruff 19개와 pytest collection 0개 기록. v2 원문과 0–55절·250 IDs 대조. / Initial plan/design/metadata review, 15 isolated synthetic checks, read-only DB/hashes, historical 19 Ruff findings and zero collected pytest tests; comparison of v2 sections 0–55 and 250 IDs. | 세부 내용 검토 대기 / Substantive review pending |
| 2026-09-28 후속 / Follow-up | Codex | 당시 9/30 PyPI·DOI 목표와 사용자 실행 방식의 3일 계획 작성, 소스 해시 불변 확인. 현재 일정은 마스터플랜으로 대체. / Drafted the then-current three-day, user-run plan targeting September 30 PyPI/DOI and checked unchanged source hashes. Superseded by the current master plan. | 대기 / Pending |
| 2026-09-29 | Codex | 복제본 recovery 코드와 합성 tests 제공. 최초에는 AST·source hash만 확인했고 실행하지 않음. 이후 사용자 보고의 5-test/subset 성공을 기록하고 추가 restore rehearsal test 제공. / Supplied copied-archive recovery code and synthetic tests; initially checked only AST/source hashes without execution. Later recorded user-reported five-test/subset success and added restore-rehearsal coverage. | 당시 새 전체 검증은 사용자 실행 대기였음 / New full validation was pending user execution at that time |
| 2026-09-30 | Codex | 공개 repo 원칙 반영, 선택된 파일/history token 패턴 읽기 전용 점검. GCAT 복제본 OOM 진단. 제품 게시·전수 보안 인증은 하지 않음. / Reflected public-repository policy, read-only selected file/history token scans and GCAT copied-archive OOM diagnosis. No publication or comprehensive security certification. | 대기 / Pending |
| 2026-10-03 출시 검사 / Release audit | Codex | README·배너·문서·TODO, API 확인, 전체 249 tests, 6 fresh-wheel environments, strict Twine 및 metadata/내용 검사. recovery helper timezone digest 최소 수정과 회귀 test; package 기능·성능은 변경하지 않음. / README/banner/docs/TODO, API review, 249 full tests, six fresh-wheel environments, strict Twine and metadata/content checks; minimum recovery-helper timezone-digest fix and regression test, without package feature/performance changes. | 사용자 최종 검토·업로드 승인 대기 / Final user review and upload approval pending |
| 2026-10-03 문서 통합 / Documentation consolidation | Codex | 메인 1·2의 제공 대화와 기존 계획을 대조, 한/영 문서·250-ID 추적·통합 master 작성. 원본 백업 및 코드 freeze 해시 확인. 문서 변경 후 artifact 재검증 결과는 release report에 기록. / Compared available Main 1/2 conversation content and existing plans; authored bilingual docs, 250-ID traceability and consolidated master. Preserved original backups and checked code-freeze hashes. Post-edit artifact verification is recorded in the release report. | 내용 검토 대기 / Substantive review pending |

역사적 검증 수와 현재 테스트 수는 다른 snapshot이다. 과거 기록을 이번에 다시 수행했다고 주장하지 않는다. 기존 기여 전체를 감사한 기록이나 저널 정책 준수 인증이 아니다. / Historical and current test counts refer to different snapshots. Earlier checks are not claimed as newly rerun. This is neither a complete audit of earlier contributions nor journal-policy certification.

## 기록 원칙 / Recording rules

- 수행하지 않은 검증·사람 검토를 완료 처리하지 않는다. 최종 결정자는 사용자다. / Never mark unperformed validation or human review complete. The user makes final decisions.
- 주요 설계 근거는 ADR, 현재 계획은 통합 master, 실행 증거는 release report에 둔다. / Keep design rationale in ADRs, current plans in the master and execution evidence in the release report.
- 비밀값·계정정보·제한 자료는 기록하지 않는다. / Do not record secrets, account information or restricted data.
- 외부 투고 시 최신 disclosure 정책을 확인한다. 원래 기록은 문서 백업에 보존한다. / Recheck disclosure policies at submission; preserve original records in the documentation backup.

[마스터플랜 / Master plan](docs/ORBITOBY_MASTER_PLAN.md) · [릴리스 보고서 / Release report](docs/RELEASE_0_1_0_REPORT.md)
