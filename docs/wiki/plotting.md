# 플롯 / Plotting

canonical DataFrame에 `archive.plot(frame, kind="line")` 또는 `kind="scatter"`를 사용합니다. [빠른 시작](../../examples/science_day.py)에 완전한 예제가 있습니다.

Use `archive.plot(frame, kind="line")` or `kind="scatter"` with a canonical DataFrame. The [quick start](../../examples/science_day.py) provides a complete example.

반환형은 `PlotResult`이며 `svg`, `data`, `provenance`를 포함합니다. 지원 노트북에서는 `_repr_svg_()`로 표시하고 `result.save("quicklook.svg")`로 저장합니다. 0.1.0의 자체 export는 SVG뿐이며 Matplotlib·Seaborn·Plotly를 설치할 필요가 없습니다.

The return type is `PlotResult`, containing `svg`, `data`, and `provenance`. Supporting notebooks display `_repr_svg_()`; save with `result.save("quicklook.svg")`. Native 0.1.0 export supports SVG only and needs no Matplotlib, Seaborn, or Plotly.

`fields`, `title`, `legend`, `width`, `height`를 지정할 수 있습니다. 서로 다른 단위·빈 데이터·그릴 값이 없는 입력은 거부합니다. 결측에서는 선이 끊기며, 서로 다른 단위를 자동 다중 패널로 나누는 기능은 없습니다.

Options include `fields`, `title`, `legend`, `width`, and `height`. Mixed units, empty data, and inputs without plottable values are rejected. Missing values break lines; mixed units are not automatically split into panels.

연결선은 관측 사이의 그림 요소일 뿐 보간 관측값이나 연속 coverage를 생성하지 않습니다. 이산 관측은 scatter가 적절할 수 있습니다. 고급 논문 그림은 사용자가 DataFrame을 외부 도구에 전달해 만듭니다.

Connecting lines are visual elements, not interpolated observations or evidence of continuous coverage. Scatter can be appropriate for discrete observations. For publication figures, users can pass DataFrames to external tools.

`archive.plot_timeseries(...)`는 조회 후 플롯하므로 네트워크를 사용할 수 있습니다. 반면 이미 받은 frame의 `archive.plot(frame)`는 표시 계층입니다. [결정 기록](../adr/2026-10-02-native-svg-plotting.md)을 참고하세요.

`archive.plot_timeseries(...)` queries before plotting and may use the network. By contrast, `archive.plot(frame)` presents an existing frame. See the [decision record](../adr/2026-10-02-native-svg-plotting.md).
