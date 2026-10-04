# ADR — 자체 SVG 간단 플롯 / Native SVG quick-look plotting

상태: 채택 · 결정일: 2026-10-02 · 문서 갱신: 2026-10-03. 과거 “Architecture v1.1”은 설계 문서 표기이며 패키지 출시 버전은 0.1.0이다. / Status: accepted · Decision: 2026-10-02 · Documentation updated: 2026-10-03. The former “Architecture v1.1” was a design-document label; the package release is 0.1.0.

## 배경과 결정 / Context and decision

Canonical 연구 시계열을 바로 확인하는 line/scatter, UTC 축, 단위·제목·범례, source/dataset label, provenance를 가진 PlotResult, Jupyter SVG 표시와 SVG 저장이 필요하다. 이를 위해 범용 plotting 프레임워크를 추가하지 않고 Python 표준 라이브러리와 기존 tabular 계층으로 SVG를 그린다. / Quick inspection requires line/scatter plots, UTC axes, units, titles, legends, source/dataset labels, a provenance-aware PlotResult, Jupyter SVG display and SVG saving. Use the Python standard library and existing tabular layer rather than adding a general-purpose plotting framework.

기본 `pip install orbitoby`로 사용할 수 있으며 plotting extra는 필요 없다. 호환되는 여러 canonical series를 한 축에 표시할 수 있다. / The normal `pip install orbitoby` includes plotting; no plotting extra is needed. Multiple compatible canonical series can share an axis.

## 과학 계약 / Scientific contracts

- 보간·평활·forward fill·resampling·canonical 값 변경을 하지 않는다. / No interpolation, smoothing, forward fill, resampling or canonical-value changes.
- 결측은 결측으로 유지하고 선을 끊는다. provider fill을 물리 관측처럼 표시하지 않는다. / Preserve missingness and break lines at missing values; never plot provider fill as physical observations.
- 호환되지 않는 단위를 한 y축에 조용히 합치지 않는다. / Never silently combine incompatible units on one y-axis.
- 렌더러는 provider payload가 아닌 canonical/provenance 자료를 읽는다. / The renderer reads canonical/provenance data rather than provider payloads.

## 경계 / Boundary

```text
Provider → raw → native normalization → canonical + provenance
         → ResearchAPI → SVG presentation
```

렌더러 자체는 읽기 전용 표현 계층이다. 다만 편의 API `archive.plot_timeseries()`는 먼저 시계열을 요청하므로 자료 취득이 발생할 수 있다. 그래프 편의 호출 전체가 항상 offline이라고 해석하지 않는다. / The renderer itself is a read-only presentation layer. The convenience API `archive.plot_timeseries()` first requests a timeseries and may therefore retrieve data. The whole convenience call is not necessarily offline.

## 후속 범위 / Future scope

복잡한 다중 패널·통계 시각화·과학 투영·대시보드·고급 styling·출판용 layout·내장 PNG/PDF 렌더링은 현재 core 범위 밖이다. DataFrame을 다른 시각화 도구로 넘길 수 있다. 현재 범위와 이후 계획은 [마스터플랜](../ORBITOBY_MASTER_PLAN.md#roadmap)을 따른다. / Complex panels, statistical systems, scientific projections, dashboards, advanced styling, publication layouts and built-in PNG/PDF rendering are beyond the current core. DataFrames can be passed to other visualization tools. Follow the [master plan](../ORBITOBY_MASTER_PLAN.md#roadmap) for current and future scope.
