# Credentials와 보안 / Credentials and security

`CredentialManager` 탐색 순서는 runtime → 선택 OS keyring → 환경변수 → Colab Secrets → 명시적 dotenv입니다. `.env`는 import만으로 로드하지 않습니다. 예제/진단의 `--allow-dotenv`는 저장소 root .env를 명시적으로 허용합니다. 값을 출력하거나 커밋하지 않습니다.

Credential resolution is runtime → optional keyring → environment → Colab Secrets → opt-in dotenv. Import alone does not load .env. Example/diagnostic --allow-dotenv opts into the repository root file. Never print or commit values.

| Provider | 환경변수 / Environment |
|---|---|
| Space-Track | SPACETRACK_USERNAME, SPACETRACK_PASSWORD |
| DISCOS | ORBITOBY_DISCOS_TOKEN |

`set_runtime/clear_runtime/resolve/get/status`로 세션 credential을 관리합니다. status는 configured/source만 반환합니다. `set_keyring/delete_keyring`는 선택 keyring 패키지를 요구합니다. DISCOS는 custom 환경변수 이름이므로 직접 resolve할 때 env_name도 지정하세요.

Use the manager methods for session credentials; status returns configured/source metadata. Keyring mutations require the optional keyring package. Pass the custom env_name when resolving DISCOS directly.

HTTP client는 HTTPS·host allowlist·크기·redirect·timeout 제한을 적용합니다. 소스별 연결 실패와 인증 거부는 다릅니다. plugin은 신뢰한 코드로 사용자 권한에서 실행되고 완전한 sandbox가 아닙니다. archive/raw에는 공개 자료 외에 민감한 요청 맥락이 들어갈 수 있으므로 공유 전에 검토하세요.

HTTP policy applies HTTPS, allowlists, size, redirect and timeout limits. Connectivity and authentication failures differ. Trusted plugins execute with user permissions, not a full sandbox. Review raw archives and request context before sharing.
