# 데이터·우주물체 탐색 / Dataset and object discovery

사용자 정의 소스·플러그인이 없는 깨끗한 Archive에서 기본 제공처 **15개**, curated dataset **103개**를 확인했습니다. 각 기관의 모든 데이터를 포괄한다는 뜻은 아닙니다.

A clean Archive without custom sources or plugins contains **15 built-in providers** and **103 curated datasets**. This is not a catalogue of everything held by each institution.

```python
from orbitoby import Archive

with Archive() as archive:
    print(archive.sources_available())
    rows = archive.datasets(metric="f107_observed", live=False)
    info = archive.dataset_info("nrcan", "f107_measurements")
    print(len(rows), info["dataset"])
```

`datasets()`는 메타데이터 dict의 list를 반환합니다. `source`, `metric`, `category`, `data_scope`, `object_scope`로 필터링하며 기본값은 `live=False`입니다. canonical metric·unit·cadence·객체 범위 등은 해당 메타데이터에서 확인합니다.

`datasets()` returns a list of metadata dictionaries. Filter with `source`, `metric`, `category`, `data_scope`, or `object_scope`; `live=False` is the default. Inspect canonical metrics, units, cadence, and object scope in those records.

`dataset_info("nrcan", "f107_measurements", live=True)`처럼 명시적으로 live 조회를 요청합니다. 정적 정보·제공처 응답·unknown을 구별하고 오류 필드를 확인하세요. 가용 기간 미상은 관측 없음의 증거가 아닙니다.

Request live metadata explicitly, for example with `dataset_info("nrcan", "f107_measurements", live=True)`. Distinguish static information, provider responses, and unknown values, and inspect errors. Unknown availability is not evidence of absent observations.

`data_scope`와 `object_scope`를 함께 읽습니다. NRCan 전역 지수, Swarm A/B/C 고정 위성 자료, 우주물체 catalogue, 사건 자료를 같은 것으로 취급하지 않습니다. 수천 개 객체를 dataset 목록에 섞지 않습니다.

Read `data_scope` and `object_scope` together. Global NRCan indices, fixed Swarm A/B/C products, object catalogues, and event data have different meanings. Large object populations are not expanded into the dataset list.

`archive.objects(search="ISS", limit=20)`는 로컬에 이미 색인된 객체만 검색합니다. `norad_id`, `cospar_id`, `source`, `dataset`, `properties`, `offset`도 지원합니다. 기본 검색은 catalogue를 자동 다운로드하지 않으며 이름만으로 객체를 병합하지 않습니다. 미수집 저장소의 0행은 전 세계 대상 없음이 아닙니다.

`archive.objects(search="ISS", limit=20)` searches only locally indexed objects. It also accepts `norad_id`, `cospar_id`, `source`, `dataset`, `properties`, and `offset`. Default search does not download catalogues or merge identities by name. Zero rows in an unpopulated archive do not mean no objects exist globally.

`source_info()`, `credits()`, `licenses()`는 등록 소스의 설명·정책을 보여줍니다. 특정 결과 행에 실제로 기여한 출처만 추린 자동 인용 보고서와는 다릅니다.

`source_info()`, `credits()`, and `licenses()` describe registered sources and policies. They are not automatic citation reports restricted to sources contributing to a particular result.

## 객체 상세·레코드·재색인 / Details, records and reindex

`search(norad_id=..., cospar_id=..., name=..., properties=...)`는 명시적 ID·속성을 검색합니다. `object(object_id=...)`는 객체 상세, `records(object_id=..., source=..., dataset=...)`는 원본 source 주장과 identity 상태를 조회합니다. `reindex(source=..., dataset=..., batch_size=500, progress=True)`는 저장 raw를 검증·정규화해 identity 색인을 재구축합니다. 네트워크 재조회나 모든 canonical cache의 강제 갱신 명령이 아닙니다.

`search(...)` searches explicit IDs/properties; `object(object_id=...)` returns details; `records(...)` exposes provider assertions and identity state. `reindex(...)` verifies and normalizes archived raw artifacts to rebuild identity indexing. It is not a network refresh or a general canonical-cache refresh operation.

이름만으로 객체를 합치지 않으며 충돌하는 ID는 기록됩니다. 물리량 속성은 지원된 projection만 검색할 수 있고 DISCOS의 원본 metadata가 모두 canonical identity 속성으로 편입되는 것은 아닙니다.

Names alone do not merge identities, and conflicting IDs are recorded. Only supported property projections are searchable; DISCOS native metadata is not entirely mapped to canonical identity properties.

[기간 모집단 / Period population](population.md) · [정확한 signature / Signatures](api-inventory.md)
