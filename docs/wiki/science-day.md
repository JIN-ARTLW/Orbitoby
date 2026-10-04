# Science Day 실행 예제 / Research workflow

[examples/science_day.py](../../examples/science_day.py)는 날짜 2024-05-10 UTC 하루를 시연합니다. 39452(Swarm A)는 명시적으로 선택한 예제이며 통계적으로 대표적인 cohort가 아닙니다.

The example demonstrates one UTC day, 2024-05-10. NORAD 39452 (Swarm A) is explicitly selected for demonstration, not a statistically representative cohort.

```bash
.venv/bin/python examples/science_day.py --allow-dotenv
```

전체 SATCAT → 기간 throughout payload → Swarm A historical orbit 및 LEO 범위 screening → GFZ F10.7/Kp/ap/Ap → Kyoto Dst → CDAWeb OMNI solar wind → Swarm POD → 명시적 GFZ forcing → NRLMSIS 2.1 → one-to-one exact merge 순서입니다. source별 실패를 독립 보고하며 다른 검증 가능한 단계를 계속합니다. 하나라도 FAIL/SKIP이면 exit 1입니다.

Stages are complete SATCAT, period payloads, selected historical orbit/LEO screening, GFZ indices, Kyoto Dst, CDAWeb OMNI wind, Swarm POD, explicit forcing, MSIS and validated exact merging. Failures are reported separately while independent stages continue; any FAIL/SKIP exits 1.

출력은 기본 `/tmp/orbitoby-science-day/`의 단계별 JSON Lines와 report.json입니다. JSON은 공유용 예시 export이며 canonical/product Parquet와 raw가 재현성 원본입니다. 위성 전체를 GP_HISTORY로 bulk 조회하지 않으며 물리/임무 metadata completeness 평가·QC·cohort·항력/감쇠 분석은 연구자가 추가해야 합니다. DISCOS는 token을 설정해 fetch할 수 있으나 예제가 불완전한 mass를 채우지는 않습니다.

Stage JSON Lines and report.json default to /tmp/orbitoby-science-day/. JSON is a sharing example; raw and canonical/product archives remain the reproduction source. The script does not request GP_HISTORY for all satellites or decide metadata completeness, QC, cohorts, drag or decay. DISCOS metadata can be fetched with a token; missing mass is not fabricated.

[실행 증거 / Execution evidence](../RELEASE_0_1_0_REPORT.md) · [모델 / Models](models.md) · [제약 / Limitations](limitations.md)
