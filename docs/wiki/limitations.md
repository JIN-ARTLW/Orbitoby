# 제약과 재현성 / Limitations and reproducibility

v0.1.1은 alpha 연구 소프트웨어입니다. 지원 API·tests 통과·특정 live 실행·과학적 모델 정확성·논문 결론은 서로 다른 증거입니다. 테스트 수를 정확성 비율로 해석하지 않습니다.

Version 0.1.1 is alpha research software. Supported APIs, regression success, a live run, scientific model accuracy and publication conclusions require different evidence.

- provider 장애·rate limit·권한·기간 미지원은 남습니다. / Outages, rate limits, access restrictions and unavailable periods remain possible.
- 최신 SATCAT의 과거 existence와 역사적 orbit은 다른 데이터입니다. / Retrospective SATCAT existence and historical orbital records are different evidence.
- metadata 부족·selection bias·관측 품질을 자동 보정하지 않습니다. / Missing metadata, selection bias and observation quality are not automatically corrected.
- 중심 81일 forcing은 미래 자료를 포함해 예측 실험의 look-ahead 위험이 있습니다. / Centered forcing includes future data and can leak information in predictive studies.
- source_preference는 첫 binding 선택이며 장애 시 다음 source로 runtime fallback하지 않습니다. / Source preference chooses the first matching binding, not runtime outage fallback.
- NRCan mergeable 제품은 같은 source의 명시된 binding에 한해 함께 반환될 수 있습니다. source 간 blending이 아닙니다. / Declared mergeable NRCan products can be returned together within that source; this is not cross-source blending.
- `preferred`는 사용자가 요청한 선택 정책이며 duplicate 사실을 해결하지 않습니다. MSIS 자동 입력 경로는 all을 사용해 duplicate 유효 driver를 거부합니다. / Explicit preferred selection is not conflict adjudication; MSIS construction preserves all claims and rejects duplicate valid drivers.
- identical GP ID dedup와 최신 SATCAT projection은 완전한 versioned claim 조회가 아닙니다. raw는 보존됩니다. / Legacy GP-ID dedup and latest SATCAT projection are not full versioned claim queries; raw remains archived.
- 범용 CLI, derive/export/cohort engine, orbit propagation, drag/causal decay 분석은 제공하지 않습니다. / There is no general CLI, derive/export/cohort engine, propagation, drag or causal-decay analysis.

재현에는 정확한 소스 revision·환경·query·시간대·raw SHA-256·canonical/model hash·quality 정책·forcing/trajectory lineage·변환 버전을 기록하세요. 공개 릴리스에서는 사용한 Orbitoby 버전과 release artifact를 함께 기록하세요.

Record source revision, environment, queries, timezone, raw and product hashes, quality policy, forcing/trajectory lineage and transform versions. For public releases, also record the Orbitoby version and release artifact used.
