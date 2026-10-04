# 소스와 dataset 탐색 / Sources and discovery

`datasets(source=None, metric=None, category=None, data_scope=None, object_scope=None, live=False)`는 dict 목록을 반환합니다. `dataset_info(source, dataset, live=False)`는 단일 설명입니다. `source_info()`, `credits()`, `licenses()`는 등록 source의 메타데이터를 반환하며 실제 결과만을 위한 자동 인용문은 아닙니다.

`datasets(...)` returns metadata dictionaries and `dataset_info(...)` describes one dataset. `source_info()`, `credits()` and `licenses()` describe registered providers; they are not automatic citations limited to one result.

`live=True`는 provider의 discovery를 요청합니다. 정적 지원 목록, live 응답, 조회 실패, 미상 기간을 구별하세요. live 성공은 모든 시각의 데이터 존재나 canonical 지원을 보장하지 않습니다. CDAWeb/LISIRD의 live catalogue는 curated 목록보다 클 수 있습니다.

`live=True` requests provider discovery. Distinguish static support, live responses, errors and unknown availability. Discovery success does not prove data coverage or canonical support. CDAWeb/LISIRD live catalogues can exceed curated lists.

```python
with Archive() as archive:
    info = archive.dataset_info("swarm", "density_a_pod", live=True)
    raw = archive.fetch(source="discos", dataset="objects", norad_id=39452)
```

마지막 조회에는 사용자 DISCOS token이 필요합니다. `fetch()`는 provider-native DataFrame을 반환하고 기본적으로 raw를 보존합니다. 날짜/ID/선택 파라미터는 adapter별로 다릅니다. 고정 위성 Swarm, 전역 지수, object catalogue, 사건 자료를 동일한 객체별 시계열로 가정하지 마세요.

The last query needs a user DISCOS token. `fetch()` returns provider-native rows and archives raw data by default. Date, ID and selection parameters depend on the adapter. Swarm fixed-spacecraft products, global indices, object catalogues and events have different scopes.

전체 내장 dataset·canonical metric 매핑은 [생성한 inventory](api-inventory.md)에 있습니다. URL 등록은 canonical mapping을 자동 추론하지 않습니다.

See the [generated inventory](api-inventory.md) for every built-in dataset and canonical mapping. URL registration does not infer canonical bindings.
