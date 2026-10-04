# 개요 / Overview

Orbitoby 0.1.0은 raw 자료, canonical 시계열, 우주물체 catalogue, historical orbit 및 명시적 MSIS 계산을 연결하는 연구 패키지입니다. 분석 가설·cohort·항력 계수·통계 결론을 자동 결정하지 않습니다.

Orbitoby 0.1.0 connects raw acquisition, canonical time series, object catalogues, historical orbit and explicit MSIS evaluation. It does not decide hypotheses, cohorts, drag coefficients or statistical conclusions.

**Orbitoby core never guesses the data.**

코어는 결측 관측을 보간·평활·resample·ffill·bfill하지 않습니다. 여러 source의 값을 암묵적으로 섞지 않습니다. 모델이 요구하는 명시적 81일 F10.7 평균과 Ap 평균은 별도의 forcing 변환이며 관측을 채우는 과정이 아닙니다.

The core does not interpolate, smooth, resample or fill missing observations, or implicitly blend source values. Explicit model-defined 81-day F10.7 and Ap means are forcing transforms, not filled observations.

```python
from orbitoby import Archive

with Archive() as archive:
    print(archive.sources_available())
    print(archive.datasets(metric="kp", live=False))
    frame = archive.timeseries(
        "kp", source="gfz", dataset="kp", start="2024-05-10", end="2024-05-11"
    )
    archive.plot(frame, kind="scatter").save("kp.svg")
```

Archive 생성은 저장소를 열며 기본 source registry를 구성합니다. context manager를 쓰거나 `close()`로 연결을 닫으세요. `Archive(credentials=..., allow_dotenv=False)`로 credential 정책을 지정합니다.

Creating Archive opens storage and builds its source registry. Use its context manager or `close()`. Set credential policy with `Archive(credentials=..., allow_dotenv=False)`.

[전체 기능·signature 목록 / Complete API inventory](api-inventory.md) · [실제 workflow / Workflow](science-day.md)
