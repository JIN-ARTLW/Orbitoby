# v0.1.0 기능 동결 / Feature freeze

결정: 기존 공개 Archive·canonical/window·SVG·catalogue/population·historical orbit·Swarm·MSIS·storage·extension 계약을 release candidate 범위로 고정합니다. 새 연구 기능·CLI·성능 확장은 중단합니다. 검증에서 드러난 최소 결함 수정, 문서·예제·진단·패키징만 허용합니다.

Decision: freeze existing public APIs and semantics as the release candidate. Stop new research features, general CLI and performance expansion. Only demonstrated defect corrections, documentation, examples, diagnostics and packaging remain in scope.

이번 최소 수정은 `msis_inputs()`의 숨은 preferred 선택을 제거해 duplicate valid drivers를 거부하고 모든 driver 행의 artifact provenance를 요구합니다. 직접 요청한 `timeseries(artifact_resolution="preferred")`는 기존 공개 계약으로 유지합니다.

The minimal correction removes hidden preferred selection inside msis_inputs and requires provenance on every driver row. Explicit user-requested timeseries preferred selection remains an existing API contract.

확인한 no-guess 경계: canonical fill 표지 보존, window exact equality와 duplicate 오류, complete MSIS day/bin 요구, observed provider_derived/model_output 분리, ProductParent 존재 검증. 최신 SATCAT projection, identical GP ID dedup, provider QC 미적용 등 남은 제약은 [위키](../wiki/limitations.md)에 명시합니다.

Verified boundaries include explicit missing markers, exact alignment and duplicate rejection, complete forcing, observed/model separation and parent validation. Remaining projection/dedup/QC limits are documented in the wiki.

`[project.scripts]`는 없으며 scripts/check_connections.py는 저장소 진단 도구입니다. 배포물 빌드/검증은 최대 3회, 성공 시 중단합니다. PyPI 업로드, commit/tag, remote push는 이번 작업에 포함하지 않습니다. 기존 사용자 변경은 보존합니다.

There is no project.scripts entry; the diagnostic is a repository script. Build/validation permits at most three attempts and stops on success. No PyPI upload, commit/tag or remote push is performed. Existing user changes are preserved.

동일 GP ID의 상충 내용을 INSERT OR IGNORE로 숨기지 않도록 검사합니다. 동일 내용의 재수집만 idempotent하게 유지합니다. / Conflicting content for an existing GP ID now raises; only identical repeated records remain idempotent.
