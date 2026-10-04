# 출처와 과학적 의미 / Provenance and scientific semantics

**Orbitoby core never guesses the data. / Orbitoby 코어는 데이터를 추측하지 않습니다.**

canonical 행은 source/dataset·원 field/value·단위·품질/상태·가능한 artifact/retrieval 정보·변환과 버전을 보존합니다. 분석·내보내기 때 값 열만 남기면 중요한 문맥을 잃습니다.

Canonical rows preserve source/dataset, original fields/values, units, quality/status, available artifact/retrieval information, and transforms/versions. Keeping only the value column loses important analytical context.

canonical 시계열 구간은 UTC `[start,end)`이며 exact timestamp 정렬은 보간·채움·평균·충돌 조정을 뜻하지 않습니다. `unknown`은 그대로 남기고 provider 결측 표지는 물리적 0으로 바꾸지 않습니다. `orbit()`도 날짜 단위 `[start,end)`입니다.

Canonical time-series intervals use UTC `[start,end)`. Exact timestamp alignment does not imply interpolation, filling, averaging, or conflict resolution. Unknown status remains unknown, and provider missing markers do not become physical zero. `orbit()` also uses date-based `[start,end)`.

관측, provider-adjusted/derived, Orbitoby-derived, model output은 구별합니다. observed F10.7·adjusted F10.7·Series D는 같은 sfu 단위를 써도 서로 바꿔 쓰지 않습니다. Swarm ACC와 POD 계열도 방법·품질 맥락을 유지합니다.

Measurements, provider-adjusted/derived products, Orbitoby-derived products, and model outputs remain distinct. Observed F10.7, adjusted F10.7, and Series D are not interchangeable merely because they use sfu. Swarm ACC and POD products also retain their method and quality context.

raw artifact는 저장 시 SHA-256과 manifest를 갖습니다. 파생·모델 제품은 입력 lineage·parameter·변환 버전을 기록합니다. archive 보존이 재배포 권한을 부여하지는 않습니다.

Archived raw artifacts carry SHA-256 and manifests. Derived/model products record input lineage, parameters, and transformation versions. Archiving does not grant redistribution rights.

source/dataset metadata와 `credits()`·`licenses()`를 확인해 원 제공처 조건을 따르세요. 소프트웨어 버전, 실제 dataset·조회 맥락, 모델 문헌을 인용합니다. 확인된 DOI가 없으므로 임의로 만들지 않습니다.

Use source/dataset metadata and `credits()`/`licenses()` to identify original provider terms. Cite the software version, actual datasets and retrieval context, and model literature. No DOI is invented when none has been verified.
