# 릴리스와 버전 / Release and versioning

## 현재 공개 버전 / Current public release

Orbitoby의 현재 공개 버전은 **v0.1.1**입니다.

The current public Orbitoby release is **v0.1.1**.

```bash
python -m pip install orbitoby
```

```python
import orbitoby

print(orbitoby.__version__)
```

v0.1.1은 v0.1.0 Science Day workflow를 유지하면서 Google Colab 호환 dependency floor와 공개 `orbitoby.__version__`을 제공하는 compatibility patch입니다.

v0.1.1 is a compatibility patch that preserves the v0.1.0 Science Day workflow while restoring Google Colab-compatible dependency floors and exposing `orbitoby.__version__`.

## 공개 artifact 불변성 / Published artifacts are immutable

이미 공개한 tag, GitHub Release, PyPI artifact를 덮어쓰지 않습니다.

Published tags, GitHub Releases, and PyPI artifacts are not rewritten.

수정이 필요하면 새 버전을 발행합니다.

Corrections require a new version.

## Release validation

배포 전에는 저장소의 `docs/release.md` 정책을 따릅니다. 핵심 gate에는 다음이 포함됩니다.

For future releases, follow the repository release policy in `docs/release.md`. Core gates include:

```bash
.venv/bin/ruff check --no-cache .
.venv/bin/ruff format --check --no-cache .
git diff --check
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -W error -m pytest -q -p no:cacheprovider
```

또한 fresh isolated build, Twine strict check, clean base/models install, artifact content/security inspection을 수행합니다.

The release process also performs a fresh isolated build, strict Twine validation, clean base/models installs, and artifact content/security inspection.

## v0.1.1 검증 범위 / v0.1.1 validation scope

v0.1.1에서는 다음을 검증했습니다.

v0.1.1 validation covered:

- Python 3.12 / 3.13 regression
- Colab-compatible dependency baseline
- built-wheel install without unnecessary compatible baseline upgrades
- Python 3.14 base/models install
- public package version API
- Science Day end-to-end workflow
- Swarm observed/provider-derived vs MSIS model-output separation
- exact 2,880 timestamp matches for the validated 2024-05-10 one-day fixture
- GitHub Release and PyPI artifacts

특정 fixture의 행 수는 일반 날짜에 대한 API 계약이 아닙니다.

Row counts from a specific validation fixture are not a general API contract for arbitrary dates.

## 변경 기록 / Change history

- **v0.1.1** — Colab compatibility patch and public package version
- **v0.1.0** — first public alpha research-software release

세부 release validation 문서는 repository `docs/RELEASE_0_1_*.md`에서 확인할 수 있습니다.

Detailed release-validation reports are available in the repository under `docs/RELEASE_0_1_*.md`.
