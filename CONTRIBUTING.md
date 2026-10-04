# 기여 안내 / Contributing

Orbitoby는 공개 연구 소프트웨어입니다. 현재 0.1.0 기능·성능 코드는 freeze 상태이며 확인된 오류의 최소 수정만 검증 후 반영합니다. 이후 기능은 [통합 계획](docs/ORBITOBY_MASTER_PLAN.md#roadmap)에 기록합니다.

Orbitoby is public research software. Feature and performance code is frozen for 0.1.0; only minimal, verified defect corrections belong in the candidate. Record later features in the [consolidated plan](docs/ORBITOBY_MASTER_PLAN.md#roadmap).

## 개발 환경과 확인 / Development and checks

```bash
uv sync
.venv/bin/ruff check --no-cache .
.venv/bin/ruff format --check --no-cache .
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -B -W error -m pytest -q -p no:cacheprovider
```

전체 검사와 배포 확인은 [release.md](docs/release.md)를 따릅니다. 로컬 handoff 테스트가 없는 checkout은 이전 전체 249개보다 적게 수집될 수 있습니다. 숫자만 맞추려고 테스트를 추가·제외하지 않습니다.

Follow [release.md](docs/release.md) for complete verification. A checkout without local handoff tests may collect fewer than the previously reported 249 total. Do not add or exclude tests merely to match a count.


- 핵심 설계·과학적 판단의 최종 결정자는 사람입니다. / Humans make final architectural and scientific decisions.
- AI 보조 변경도 실제 검증과 사람 검토를 구별해 기록합니다. / Record actual validation and human review separately for AI-assisted changes.
- 기존 API·연구 데이터를 보호하고 migration은 복제본에서 검증합니다. / Protect existing APIs/data and validate migrations on copies.
- 새 source는 출처·권리·인증·필드/단위·fixture·제한된 live 증거를 갖춰야 합니다. / New sources require provenance, rights, auth, field/unit, fixture, and bounded live evidence.
- 비밀값·사용자 raw/DB를 commit하지 않습니다. / Never commit secrets or user raw/DB files.
- 문서는 한·영 병기하며 ADR에는 주요 선택 이유를 남깁니다. / Keep docs bilingual and record major design rationale in ADRs.
- commit 유형 / commit types: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`.

0.1.x의 공개 API·저장 형식을 v1.0 안정성 약속으로 해석하지 않습니다. 존재하지 않는 CLI나 계획 API를 문서 예제로 추가하지 마세요.

Do not treat 0.1.x APIs/storage as a v1.0 stability promise. Do not document nonexistent CLI commands or planned APIs as executable examples.
