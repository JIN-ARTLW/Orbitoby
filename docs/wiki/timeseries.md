# 시계열과 정렬 / Time series and alignment

`archive.timeseries(metric, *, start, end, source=None, dataset=None, ...)`는 long-form DataFrame을 반환합니다. 여러 물리량은 `metric` 대신 `fields=[...]`를 사용하며 둘을 동시에 넘길 수 없습니다. 실행 예제는 [빠른 시작](../../examples/science_day.py)에 있습니다.

`archive.timeseries(metric, *, start, end, source=None, dataset=None, ...)` returns a long-form DataFrame. For multiple metrics use `fields=[...]` instead of `metric`; do not pass both. See the [quick start](../../examples/science_day.py) for an executable example.

canonical 구간은 UTC `[start, end)`이며 시작 포함·끝 제외입니다. 명시적 `Z` 또는 시간대 포함 입력을 권장합니다. 현재 naive 시각도 UTC로 해석하며, 모호한 시간대 정보를 추정하지 않습니다.

Canonical intervals are UTC `[start, end)`, including the start and excluding the end. Prefer explicit `Z` or timezone-aware input. Current naive timestamps are interpreted as UTC; the API does not infer a missing local timezone.

행마다 값·단위·원 source field/value·품질·상태·artifact·변환 정보를 보존합니다. 결측을 채우지 않습니다. `source`와 필요할 때 `dataset`을 지정하세요. 여러 비병합 제품이 후보이면 dataset 선택이 필요합니다.

Rows preserve values, units, original source fields/values, quality, status, artifacts, and transforms. Missing values are not filled. Select `source` and, where needed, `dataset`; multiple non-mergeable candidate products require dataset selection.

기본 `artifact_resolution="all"`은 겹치는 주장을 보존합니다. `"preferred"`는 binding 우선순위에 따른 명시적 선택이며 평균이나 품질 판정이 아닙니다. `source_preference`도 source 선택 정책이지 데이터 혼합 허가가 아닙니다.

The default `artifact_resolution="all"` preserves overlapping claims. `"preferred"` explicitly selects by binding priority; it is neither averaging nor a quality verdict. `source_preference` selects a source rather than authorizing blending.

기본 `archive_raw=True` 경로는 raw 출처와 로컬 canonical cache를 연결합니다. `False`는 영속 cache를 우회하므로 제한을 이해한 뒤 사용하세요.

The default `archive_raw=True` path connects raw provenance and the local canonical cache. `False` bypasses persistent caching and should be used deliberately.

`window(start=..., end=..., fields=[...], source=..., dataset=...)`는 관측 timestamp의 합집합에 정확히 정렬합니다. 반환 `ResearchWindow`는 `data`, `presence`, `missing_reason`, `provenance`, `units`를 갖습니다. metric/timestamp 중복은 명시적 선택 전까지 오류입니다. 보간·forward-fill·평활·resample·묵시적 평균을 수행하지 않습니다.

`window(start=..., end=..., fields=[...], source=..., dataset=...)` aligns exactly on the union of observed timestamps. Its `ResearchWindow` contains `data`, `presence`, `missing_reason`, `provenance`, and `units`. Duplicate metric/timestamp rows raise an error until explicitly resolved. It performs no interpolation, forward fill, smoothing, resampling, or implicit averaging.

`space_weather(start=..., end=..., fields=..., source=...)`는 canonical 조회의 편의 함수입니다. 현재 `timeseries()`·`window()`에는 `norad_id`, `cadence`, `include`, `alignment` 인자가 없습니다. 과거 계획의 예시를 실행 API로 사용하지 마세요.

`space_weather(start=..., end=..., fields=..., source=...)` is a canonical-query convenience wrapper. Current `timeseries()` and `window()` do not accept `norad_id`, `cadence`, `include`, or `alignment`. Historical plan examples are not executable API contracts.

## 궤도 경계 / Orbit boundaries

`orbit()`도 날짜 기반 `[start, end)`이며 끝 날짜를 제외합니다. `sync=False`는 로컬 DB만 조회합니다.

`orbit()` also uses date-based `[start, end)`, excluding the end date. `sync=False` queries the local DB only.
