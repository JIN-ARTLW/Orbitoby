# 기여 / Contributing

Orbitoby는 연구 재현성과 provenance를 기능 수보다 우선합니다.

Orbitoby prioritizes research reproducibility and provenance over feature count.

## 시작하기 / Start

저장소의 `CONTRIBUTING.md`, `SECURITY.md`, `WORKFLOW.md`와 관련 ADR을 먼저 읽어주세요.

Read the repository's `CONTRIBUTING.md`, `SECURITY.md`, `WORKFLOW.md`, and relevant ADRs first.

개발 환경:

Development environment:

```bash
uv sync --group dev --extra models
```

기본 검증:

Basic validation:

```bash
uv run --group dev --extra models ruff check .
uv run --group dev --extra models ruff format --check .
uv run --group dev --extra models python -m pytest -q
git diff --check
```

## Source adapter 기여 / Contributing a source adapter

새 provider를 추가할 때는 단순히 HTTP endpoint를 연결하는 것만으로 충분하지 않습니다.

Adding a provider requires more than wiring an HTTP endpoint.

반드시 검토할 항목:

Required review points:

- provider identity and official documentation
- dataset semantics and units
- time convention and interval semantics
- authentication requirements
- raw payload preservation
- provenance/artifact identity
- quality/status fields
- canonical mapping, if scientifically justified
- licensing/citation/redistribution policy
- tests and failure behaviour

Canonical mapping이 불분명하면 provider-native `fetch()` 지원만 추가하고 canonical metric을 억지로 만들지 않는 편이 낫습니다.

If a canonical mapping is scientifically unclear, prefer provider-native `fetch()` support rather than inventing a canonical metric.

## 과학적 변경 / Scientific changes

다음은 특히 엄격하게 검토합니다.

The following changes require especially careful review:

- automatic interpolation or filling
- source blending
- unit conversion
- time-boundary changes
- artifact-resolution policy
- identity matching
- orbit deduplication
- model forcing construction
- provenance/lineage changes

동작을 조용히 바꾸는 대신 명시적인 API와 테스트를 선호합니다.

Prefer explicit APIs and tests over silent behavioural changes.

## 문서 / Documentation

Public API 변경에는 한/영 문서 업데이트를 같이 포함합니다.

Public API changes should include corresponding bilingual documentation updates.

코드 예시는 가능한 한 복사해서 바로 실행할 수 있게 유지합니다.

Keep code examples copy-paste runnable whenever practical.

## Pull request

기능별 branch와 일반적인 pull-request workflow를 사용합니다. Public history의 force-push/tag rewrite는 피합니다.

Use feature branches and the normal pull-request workflow. Avoid force-pushing or rewriting published tags/history.
