# 기간 모집단 / Period population

```python
with Archive() as archive:
    candidates = archive.objects(
        start="2024-05-10",
        end="2024-05-11",
        existence="throughout",
        object_type="payload",
        sync=True,
    )
```

`sync=True`는 decayed 객체를 포함한 CelesTrak 전체 SATCAT을 새로 저장합니다. `sync=False`는 저장된 최신 assertion/snapshot을 사용합니다. 현재 active GP 목록은 과거 population을 대신하지 못합니다.

`sync=True` archives the complete CelesTrak SATCAT including decayed objects; `False` uses local latest assertions/snapshots. Today's active GP catalogue is not a historical population substitute.

기간은 날짜 단위 `[start,end)`입니다. `overlap`: launch < end, decay 미기재 또는 decay ≥ start. `throughout`: launch ≤ start, decay 미기재 또는 decay ≥ end. launch 미상은 제외합니다. decay 미기재는 provider가 decay를 기록하지 않았다는 의미이지 생존이 실측 검증됐다는 뜻은 아닙니다. 현재 snapshot으로 과거 존재 조건을 평가하므로 당시 알려졌던 catalogue의 복원이 아닙니다.

The date interval is `[start,end)`. Overlap requires launch < end and absent decay or decay ≥ start. Throughout requires launch ≤ start and absent decay or decay ≥ end. Unknown launch dates are excluded. Absent decay is a provider assertion, not verified survival. This applies historical existence rules to a current snapshot, not a reconstruction of knowledge available at that time.

유형은 `payload`, `rocket_body`, `debris`, `unknown`이며 별칭 PAY/R/B/DEB/UNK도 지원합니다. temporal 조회의 `limit=None`은 전체 결과, 일반 `objects()`의 기본 limit은 100입니다. source/dataset은 CelesTrak SATCAT만 지원합니다. mass/mission/LEO 조건은 존재 필터와 별도로 검토하세요.

Types are payload, rocket_body, debris and unknown, with PAY/R/B/DEB/UNK aliases. Temporal `limit=None` returns all matches; ordinary `objects()` defaults to 100. Period selection supports only CelesTrak SATCAT. Check mass, mission and LEO criteria separately.

전체 SATCAT fast path는 raw CSV를 직접 읽습니다. 따라서 일반 local identity 검색에 모든 객체가 색인됐다고 가정하면 안 됩니다. provenance 열과 raw artifact를 보존하세요.

The bulk SATCAT fast path reads raw CSV directly; it does not imply every object is in ordinary identity search. Retain provenance columns and raw artifacts.
