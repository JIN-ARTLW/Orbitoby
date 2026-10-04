# Historical orbit와 요약 / Historical orbit and summary

```python
with Archive(allow_dotenv=True) as archive:
    orbit = archive.orbit(norad_id=39452, start="2024-05-10", end="2024-05-11")
    summary = archive.orbit_summary(
        [39452],
        start="2024-05-10",
        end="2024-05-11",
        periapsis_km=(200, 2000),
        min_coverage=1.0,
        orbit_match="all",
        sync=False,
    )
```

`orbit()`은 Space-Track GP_HISTORY만 동기화하며 기본 `sync=True`입니다. 날짜 `[start,end)`이고 provider 내부 inclusive 날짜 요청과 구분합니다. `sync=False`는 DB만 읽습니다. epoch, elements, TLE, source, artifact_id를 보존하며 궤도 전파나 결측 시각 생성은 하지 않습니다.

`orbit()` synchronizes only Space-Track GP_HISTORY, defaulting to `sync=True`. It exposes date-based `[start,end)` independently of inclusive provider requests. `sync=False` reads the DB. Epochs, elements, TLEs, source and artifact IDs remain available; there is no orbit propagation or gap filling.

`orbit_summary()`는 ID iterable 또는 `norad_id` 열을 가진 DataFrame을 받습니다. `periapsis_km`, `apoapsis_km`, `inclination_deg`, `eccentricity`, `mean_motion` 범위는 양끝 포함입니다. 기본 `sync=False`; `all`은 모든 usable record, `any`는 하나 이상의 record가 모든 범위를 만족해야 합니다. missing filter data는 통과로 추정하지 않습니다.

`orbit_summary()` accepts IDs or a candidate DataFrame with `norad_id`. Range bounds are inclusive; it defaults to local reads. `all` requires every usable record and `any` at least one record to satisfy all selected ranges. Missing filter values do not become assumed matches.

`observed_day_ratio`는 실제 레코드가 존재하는 UTC 날짜 수/요청 날짜 수입니다. 연속 관측·완전 궤도 coverage가 아닙니다. `matches`, `filter_reason`, `error`, 레코드 수·통계·artifact 수를 확인합니다. 객체별 실패는 전체 조회를 중단하지 않고 반환됩니다.

`observed_day_ratio` is dates with actual records divided by requested UTC dates, not continuous coverage. Inspect matches, reasons, errors, counts, statistics and artifact counts. Per-object errors remain in the returned table.

Legacy 궤도 DB는 GP ID primary key로 최초 색인 행을 유지합니다. 동일 GP ID의 다른 내용은 오류로 거부합니다. versioned scientific claim store는 아닙니다. 원본 artifact는 별도로 남습니다. 연구에서 revised GP를 비교하려면 raw를 확인해야 합니다.

The legacy orbit DB keeps the first indexed row per GP ID. Conflicting content for the same GP ID raises an error; this is not a versioned scientific-claim store. Raw artifacts remain separate; inspect them when comparing revised GP claims.
