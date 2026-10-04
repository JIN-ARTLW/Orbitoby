# 소스·플러그인·인증 / Sources, plugins, and credentials

`plugin_candidates()`는 `orbitoby.sources` entry point의 메타데이터를 발견합니다. `trust_source_plugin(name)`으로 명시적으로 신뢰한 Python 플러그인만 로드합니다. `untrust_source_plugin(name)`은 신뢰를 철회하고 `reload_sources()`는 registry를 갱신합니다. 플러그인은 사용자 권한으로 실행되며 완전한 sandbox가 아닙니다.

`plugin_candidates()` discovers metadata for `orbitoby.sources` entry points. Python plugins load only after explicit `trust_source_plugin(name)`. `untrust_source_plugin(name)` revokes trust, and `reload_sources()` refreshes the registry. Plugins run with user privileges and are not fully sandboxed.

신뢰 설정은 현재 이름 기준입니다. 배포물 서명·버전 고정·업데이트마다 재신뢰를 자동 보장한다고 설명하지 않습니다. 플러그인 코드를 검토하세요.

Current trust settings are name-based. They do not promise package signatures, version pinning, or automatic reapproval after every update. Review plugin code.

`register_http_source(name=..., dataset=..., url=..., format="json", root_key=None, ...)`는 HTTPS 선언형 source를 영속 등록합니다. JSON/CSV/TSV를 지원하며 `unregister_http_source(name, dataset=...)`로 해제합니다. 옛 계획의 `add_http_source()`는 현재 메서드 이름이 아닙니다.

`register_http_source(name=..., dataset=..., url=..., format="json", root_key=None, ...)` persistently registers an HTTPS declarative source. JSON, CSV, and TSV are supported; remove it with `unregister_http_source(name, dataset=...)`. The old planned `add_http_source()` is not the current method name.

Python SourceAdapter는 명시적 canonical metric binding을 제공하면 탐색→시계열→window→plot에 연결할 수 있습니다. 단순 URL 등록만으로 과학적 필드·단위·의미가 자동 매핑되지는 않습니다.

A Python SourceAdapter can join discovery → timeseries → window → plot by supplying explicit canonical metric bindings. Registering a URL alone does not infer scientific fields, units, or semantics.

설정은 archive의 `settings.json`에 저장되며 writer는 최종 파일을 `0600`으로 교체합니다. 모든 archive 파일이 자동 비공개 권한이라는 뜻은 아닙니다. URL·설정·노트북에 비밀값을 넣지 마세요.

Settings live in the archive’s `settings.json`; the writer replaces the final file with mode `0600`. This does not make every archive file private automatically. Keep secrets out of URLs, settings, and notebooks.

CredentialManager 순서는 runtime → 선택 OS keyring → 환경변수 → Colab Secrets → 명시적 `.env`입니다. `Archive(credentials=manager)`를 사용하거나 `Archive(allow_dotenv=True)`로 개발 환경의 로딩을 선택합니다. import만으로 `.env`를 로드하지 않고 평문 credential 파일을 쓰지 않습니다.

CredentialManager resolves runtime → optional OS keyring → environment → Colab Secrets → explicitly enabled `.env`. Pass `Archive(credentials=manager)` or opt into development loading with `Archive(allow_dotenv=True)`. Import alone does not load `.env`, and the credential API does not write a plaintext credential file.
