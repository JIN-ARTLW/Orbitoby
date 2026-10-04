# 설치 / Installation

Python 3.12 이상과 독립 가상환경을 사용하세요. 아래 PyPI 명령은 정식 릴리스 설치용이며, 공개 전에는 검사한 로컬 wheel을 설치합니다.

Use Python >=3.12 and a virtual environment. The PyPI commands below target the published release; before publication, install the audited local wheel.


```bash
python -m venv .venv
# macOS/Linux 활성화 / activation
source .venv/bin/activate
python -m pip install orbitoby
python -m pip install "orbitoby[models]"
```

Windows 활성화 명령은 `.venv\Scripts\activate`입니다. 로컬 wheel 설치·검사는 [릴리스 절차](../release.md)를 참고하세요.

On Windows, activate with `.venv\Scripts\activate`. See the [release procedure](../release.md) for local-wheel installation and checks.

0.1.0의 `models` extra는 `pymsis>=0.13,<0.14`를 추가합니다. 기본 탐색·저장·canonical 조회·SVG 플롯에는 필요하지 않습니다. 의존성 축소는 릴리스 이후 검토합니다.

The 0.1.0 `models` extra adds `pymsis>=0.13,<0.14`. Base discovery, storage, canonical queries, and SVG plotting do not need it. Dependency reduction is deferred until after release.

저장 위치는 기본 `~/.orbitoby`입니다. 변경하려면 Orbitoby를 import하기 전에 `ORBITOBY_DATA_DIR`를 설정하세요. `with Archive() as archive:`를 사용해 DB 연결을 닫습니다.

Storage defaults to `~/.orbitoby`. Set `ORBITOBY_DATA_DIR` before importing Orbitoby to change it. Use `with Archive() as archive:` to close the database connection.

`Archive()`는 기본적으로 `.env` 로딩을 활성화하지 않습니다. 인증 우선순위와 플러그인 신뢰 정책은 [확장 안내](extensions.md)에 있습니다.

`Archive()` does not enable `.env` loading by default. Credential precedence and plugin trust are documented in the [extension guide](extensions.md).
