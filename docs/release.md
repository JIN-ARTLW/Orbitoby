# 출시 검증 절차 / Release verification

저장소 root에서 실행한다. 기능·성능을 동결하고 기존 로컬 변경을 보존한다. 현재 게이트는 [마스터플랜](ORBITOBY_MASTER_PLAN.md#release), 실제 결과는 [보고서](RELEASE_0_1_0_REPORT.md)를 따른다. / Run from the repository root, freeze feature/performance code and preserve existing local changes. See the [master plan](ORBITOBY_MASTER_PLAN.md#release) for gates and the [report](RELEASE_0_1_0_REPORT.md) for actual results.

```bash
.venv/bin/ruff check --no-cache .
.venv/bin/ruff format --check --no-cache .
git diff --check
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -B -W error -m pytest -q -p no:cacheprovider
```

전체 pytest는 현재 checkout의 모든 발견 가능한 테스트를 실행합니다. 역사적 handoff 파일 여부로 개수는 달라질 수 있습니다. / Full pytest runs all discoverable tests in this checkout; historical handoff files can change the count.

새 출력 폴더에서 빌드하고 stale TestPyPI 파일과 섞지 않는다. / Build in a fresh output directory and do not mix stale TestPyPI artifacts with this candidate.

```bash
release_work=$(mktemp -d)
uv venv --python 3.12 "$release_work/tools"
uv pip install --python "$release_work/tools/bin/python" build twine
"$release_work/tools/bin/python" -m build --installer uv --outdir "$release_work/dist" .
"$release_work/tools/bin/python" -m twine check --strict "$release_work/dist/"*
uv venv --python 3.12 "$release_work/base"
uv pip install --python "$release_work/base/bin/python" "$release_work/dist/orbitoby-0.1.0-py3-none-any.whl"
uv pip check --python "$release_work/base/bin/python"
uv venv --python 3.12 "$release_work/models"
uv pip install --python "$release_work/models/bin/python" "$release_work/dist/orbitoby-0.1.0-py3-none-any.whl[models]"
uv pip check --python "$release_work/models/bin/python"
```

가능하면 3.13/3.14에서도 base/models를 각각 새로 설치한다. checkout 밖에서 installed site-packages import를 확인하고 offline discovery, canonical 결측/half-open 구간, cache/window, SVG, 명시적 입력 MSIS, settings 0600을 검사한다. 합성 fixture를 실제 관측으로 표현하지 않는다. 공개 provider 확인은 별도 짧은 probe로 제한한다. / Where available, repeat fresh base/models installs on 3.13/3.14. Run outside the checkout, verify installed site-packages imports and test offline discovery, canonical missingness/half-open bounds, cache/window, SVG, explicit-input MSIS and settings mode 0600. Do not present synthetic fixtures as observations. Keep public-provider checks separate and bounded.

wheel/sdist의 파일·의존성·LICENSE/NOTICE·Markdown metadata를 확인하고 `.env`, credentials/settings, 사용자 archive, local recovery 자료가 들어가지 않도록 한다. secret 패턴 검사는 제한된 탐지이며 부재 증명이 아니다. 실제 비밀값을 출력하지 않는다. / Inspect wheel/sdist members, dependencies, LICENSE/NOTICE and Markdown metadata; exclude `.env`, credentials/settings, user archives and local recovery material. Secret-pattern scans are bounded checks, not proof of absence. Never print secret values.

## 게시 게이트 / Publication gate

위 명령에는 upload가 없다. 검토한 코드·배너·문서의 공개 링크를 확인하고 정확한 artifact에 대한 명시적 사용자 승인 후에만 PyPI에 올린다. Pages의 `docs/` 활성화는 별도 repo 설정이며 수행되었다고 가정하지 않는다. / These commands do not upload. Verify public links for the reviewed code, banner and docs and upload to PyPI only after explicit approval for the exact artifacts. Enabling Pages from `docs/` is a separate repository setting and must not be assumed complete.

PyPA는 격리 build와 별도 Twine upload를 설명한다. Trusted Publishing은 설정한 identity provider와 단기 인증을 사용한다. 수동 Twine upload는 API token과 username `__token__`을 사용한다. token을 문서에 넣거나 요청하지 않는다. 삭제했더라도 같은 파일명은 재업로드할 수 없으므로 과거 TestPyPI 0.1.0에 의존하지 않는다. / PyPA documents isolated builds and separate Twine uploads. Trusted Publishing uses a configured identity provider and short-lived authentication. Manual Twine uploads use an API token with username `__token__`. Never request or put tokens in docs. Filenames cannot be reused even after deletion, so do not depend on the old TestPyPI 0.1.0.

공식 자료 확인일: 2026-10-03. / Official sources reviewed: 2026-10-03.

- [PyPA 패키징 안내 / Packaging tutorial](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
- [Twine 문서 / Documentation](https://twine.readthedocs.io/en/stable/)
- [PyPI 신뢰 게시 / Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [PyPI 토큰·파일명 재사용 / Tokens and filename reuse](https://pypi.org/help/)

## 배포물 포함 정책 / Distribution contents

wheel은 runtime 전체와 LICENSE/NOTICE, README metadata를 포함합니다. examples/scripts/docs/tests는 source distribution에 포함하며 설치형 CLI는 추가하지 않습니다. 검사 결과·hash는 빌드 후 `dist/BUILD_REPORT.md`에 기록합니다. 과거 dist의 문서 백업은 삭제하지 않고 최상위 wheel/sdist만 최신 것으로 교체합니다.

The wheel contains the complete runtime, licenses and README metadata. The sdist additionally includes examples, scripts, docs and tests; no console entry point is added. Post-build results and hashes live in dist/BUILD_REPORT.md. Preserve historical documentation backups in dist and replace only the current top-level distribution files.

[uv 파일 포함 규칙 / File inclusion](https://docs.astral.sh/uv/concepts/build-backend/)을 확인해 source-include를 설정했습니다. / source-include follows the official uv file-inclusion rules.
