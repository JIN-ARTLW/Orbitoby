# 보안 정책 / Security policy

독립 보안 인증이나 모든 버전의 보안 지원을 주장하지 않습니다. 발견된 문제는 재현 증거와 영향 범위로 평가합니다.

This is not independent security certification or a promise of security support for every version. Evaluate findings using reproducible evidence and impact.

## 비밀정보와 확장 / Secrets and extensions

사용자는 자신의 provider 계정을 사용합니다. `.env`, API key, password, token, 인증 쿠키와 비공개 archive를 공개하지 마세요. URL·manifest·notebook 출력에도 비밀을 넣지 않습니다.

Users supply their own provider credentials. Do not publish `.env`, API keys, passwords, tokens, authentication cookies, or private archives. Keep secrets out of URLs, manifests, and notebook output.

Python plugin의 명시적 trust는 sandbox가 아닙니다. 설치·업데이트할 코드를 검토하세요. `settings.json`의 `0600`은 다른 파일까지 보호한다는 뜻이 아닙니다.

Explicit trust of a Python plugin is not a sandbox. Review code before installation or updates. Mode `0600` on `settings.json` does not protect every other file.

## 취약점 제보 / Vulnerability reports

민감한 내용이나 악용 절차를 공개 Issue에 올리지 말고 관리자에게 비공개로 제보하세요. 저장소는 [JIN-ARTLW/Orbitoby](https://github.com/JIN-ARTLW/Orbitoby)입니다. 비공개 신고 기능의 활성화 여부는 이 문서에서 확인했다고 주장하지 않습니다.

Report sensitive details or exploit instructions privately to the maintainer rather than in a public issue. The repository is [JIN-ARTLW/Orbitoby](https://github.com/JIN-ARTLW/Orbitoby). This document does not claim that a particular private-reporting feature has been enabled.

최소 재현, 영향 버전, 환경, 예상/실제 동작을 비밀값 없이 전달하세요. 실제 토큰이나 전체 사용자 DB를 첨부하지 않습니다.

Provide a minimal reproduction, affected version, environment, and expected/actual behavior without secrets. Do not attach real tokens or a complete user database.
