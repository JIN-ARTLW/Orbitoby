# 연결 확인과 문제 해결 / Diagnostics and troubleshooting

저장소 root에서 한 줄 실행합니다. installed console CLI는 추가하지 않았습니다.

Run one line from the repository root. No installed console entry point is added.

```bash
.venv/bin/python scripts/check_connections.py --allow-dotenv
```

`--offline`: 등록 source 수·핵심 API·DB 임시 table·storage 임시 파일만 검사. `--timeout 20`: provider worker당 wall-clock 제한(기본 20초), 동시 worker 최대 4개. `.env`가 필요 없으면 --allow-dotenv를 생략하세요. `PASS`는 검사한 endpoint 응답이지 전체 scientific workflow 완료가 아닙니다. HAPI는 capabilities, 나머지는 소량/정해진 provider fetch를 검사합니다.

Offline mode checks registry/API, a temporary DB table and temporary storage file. Timeout bounds each provider worker (20 seconds default), at most four concurrently. Omit --allow-dotenv when unnecessary. PASS means the tested endpoint responded, not complete scientific coverage; HAPI probes capabilities and other probes use bounded provider requests.

`SKIP credential_not_configured`: 미설정. `FAIL authentication_or_access_denied`: HTTP 401/403(403은 접근정책 차단일 수도 있음). `FAIL network_*`, `provider_http_*`, `deadline_exceeded`: 네트워크/서비스/제한시간 문제. FAIL 하나 이상이면 exit 1, PASS와 SKIP만 있으면 0입니다. SKIP은 인증 성공을 뜻하지 않습니다. stderr·예외 메시지·credential은 출력하지 않습니다.

Missing credentials are SKIP. HTTP 401/403 is authentication/access denial; 403 can be policy denial. Network/provider/deadline failures are separate. Any FAIL exits 1; PASS/SKIP-only exits 0. SKIP does not prove authentication. Worker stderr, exception text and secrets are never relayed.

| 증상 / Symptom | 확인 / Action |
|---|---|
| local_api_or_storage | 다른 Archive writer를 닫고 권한·disk·lock 확인 / Close competing writers; check permissions, disk and locks |
| 여러 source/dataset / ambiguity | source와 dataset을 명시 / Specify source and dataset |
| duplicate window/forcing | raw claims 확인, 암묵적 평균 금지 / Inspect claims; do not silently average |
| missing forcing | ±40일 F10.7와 57시간 ap 확보 / Obtain complete daily/three-hour drivers |
| empty local catalogue | fetch/reindex 여부 확인 / Check ingestion/reindex; local emptiness is not global absence |
| endpoint PASS, data FAIL | 범위·제품 가용성·parser 확인 / Check interval, availability and parser |
| missing pymsis | models extra 설치 / Install the models extra |
| cache stale | archive 재현본 보존 후 별도 저장소에서 검증 / Preserve snapshot and verify using a separate archive |
