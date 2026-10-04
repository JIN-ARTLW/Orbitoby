from __future__ import annotations

import math
from dataclasses import dataclass
from html import escape
from numbers import Real
from pathlib import Path
from typing import Literal

import pandas as pd

PlotKind = Literal["line", "scatter"]

_PALETTE = (
    "#2563eb",
    "#dc2626",
    "#059669",
    "#7c3aed",
    "#d97706",
    "#0891b2",
    "#db2777",
    "#4f46e5",
)


@dataclass(slots=True)
class PlotResult:
    """Native Orbitoby SVG plot and its exact research inputs."""

    svg: str
    data: pd.DataFrame
    provenance: pd.DataFrame

    def _repr_svg_(self) -> str:
        return self.svg

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        if target.suffix.lower() != ".svg":
            raise ValueError("Orbitoby native plots are saved as .svg files.")
        target.write_text(self.svg, encoding="utf-8")
        return target


class PlotAPI:
    """Dependency-free native SVG quick-look plotting."""

    _REQUIRED_COLUMNS = frozenset(
        {"timestamp", "metric", "value", "unit", "source", "dataset"}
    )

    @classmethod
    def _validate_plot_frame(cls, frame: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("plot data must be a pandas DataFrame.")

        missing = cls._REQUIRED_COLUMNS - set(frame.columns)
        if missing:
            raise ValueError(
                "Canonical plot data is missing required column(s): "
                + ", ".join(sorted(missing))
            )

        if frame.empty:
            raise ValueError("Cannot plot an empty canonical time series.")

        result = frame.copy()
        result["timestamp"] = pd.to_datetime(
            result["timestamp"],
            utc=True,
            errors="raise",
        )
        return result.sort_values(
            ["timestamp", "metric", "source", "dataset"]
        ).reset_index(drop=True)

    @staticmethod
    def _provenance_frame(frame: pd.DataFrame) -> pd.DataFrame:
        columns = [
            column
            for column in (
                "metric",
                "source",
                "dataset",
                "source_field",
                "source_version",
                "status",
                "provider_status",
                "quality_flag",
                "artifact_kind",
                "artifact_id",
                "retrieved_at",
                "transform",
                "transform_version",
            )
            if column in frame.columns
        ]
        if not columns:
            return pd.DataFrame()
        return frame[columns].drop_duplicates().reset_index(drop=True)

    @staticmethod
    def _series_label(
        *,
        metric: str,
        source: str,
        dataset: str,
        include_source: bool,
        include_dataset: bool,
    ) -> str:
        label = metric
        qualifiers = []
        if include_source:
            qualifiers.append(source)
        if include_dataset:
            qualifiers.append(dataset)
        if qualifiers:
            label += " [" + " / ".join(qualifiers) + "]"
        return label

    @staticmethod
    def _numeric_value(value) -> float | None:
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
        except TypeError:
            pass
        if isinstance(value, bool):
            raise TypeError(
                "Boolean values cannot be plotted as scientific measurements."
            )
        if not isinstance(value, Real):
            raise TypeError("Canonical plot values must be numeric or missing.")
        result = float(value)
        if not math.isfinite(result):
            return None
        return result

    @staticmethod
    def _format_number(value: float) -> str:
        if value == 0:
            return "0"
        magnitude = abs(value)
        if magnitude >= 10000 or magnitude < 0.001:
            return f"{value:.3e}"
        return f"{value:.4g}"

    @staticmethod
    def _format_timestamp(value: pd.Timestamp, span_seconds: float) -> str:
        if span_seconds <= 2 * 86400:
            return value.strftime("%m-%d %H:%M")
        if span_seconds <= 90 * 86400:
            return value.strftime("%Y-%m-%d")
        if span_seconds <= 730 * 86400:
            return value.strftime("%Y-%m")
        return value.strftime("%Y")

    @staticmethod
    def _line(
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        stroke: str,
        width: float = 1.0,
        opacity: float = 1.0,
    ) -> str:
        return (
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" '
            f'x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{stroke}" stroke-width="{width:.2f}" '
            f'opacity="{opacity:.3f}" />'
        )

    @staticmethod
    def _text(
        x: float,
        y: float,
        value: str,
        *,
        size: int = 12,
        anchor: str = "start",
        weight: str = "normal",
        rotate: int | None = None,
    ) -> str:
        transform = ""
        if rotate is not None:
            transform = f' transform="rotate({rotate} {x:.2f} {y:.2f})"'
        return (
            f'<text x="{x:.2f}" y="{y:.2f}" '
            f'font-family="system-ui, -apple-system, sans-serif" '
            f'font-size="{size}" font-weight="{weight}" '
            f'fill="#111827" text-anchor="{anchor}"{transform}>'
            f"{escape(value)}</text>"
        )

    @staticmethod
    def _append_line_segment(
        parts: list[str],
        segment: list[tuple[float, float]],
        color: str,
    ) -> None:
        if not segment:
            return

        if len(segment) == 1:
            x, y = segment[0]
            parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.0" fill="{color}" />')
            return

        points = " ".join(f"{x:.2f},{y:.2f}" for x, y in segment)

        parts.append(
            f'<polyline points="{points}" fill="none" '
            f'stroke="{color}" stroke-width="2" '
            f'stroke-linejoin="round" stroke-linecap="round" />'
        )

    def _render_svg(
        self,
        frame: pd.DataFrame,
        *,
        kind: PlotKind,
        title: str,
        legend: bool,
        width: int,
        height: int,
    ) -> str:
        if width < 520:
            raise ValueError("width must be at least 520.")
        if height < 320:
            raise ValueError("height must be at least 320.")

        units = {str(unit) for unit in frame["unit"].dropna().unique()}
        if len(units) > 1:
            raise ValueError(
                "Orbitoby will not plot metrics with different units "
                "on one axis implicitly."
            )

        include_source = frame["source"].nunique() > 1
        include_dataset = frame["dataset"].nunique() > 1

        groups = list(
            frame.groupby(
                ["metric", "source", "dataset"],
                sort=False,
                dropna=False,
            )
        )

        valid_values = []
        for value in frame["value"]:
            numeric = self._numeric_value(value)
            if numeric is not None:
                valid_values.append(numeric)

        if not valid_values:
            raise ValueError(
                "Canonical plot data contains no plottable numeric values."
            )

        x_min = frame["timestamp"].min()
        x_max = frame["timestamp"].max()
        if x_min == x_max:
            x_min -= pd.Timedelta(minutes=30)
            x_max += pd.Timedelta(minutes=30)

        y_min = min(valid_values)
        y_max = max(valid_values)

        if y_min == y_max:
            pad = max(abs(y_min) * 0.05, 1.0)
            y_min -= pad
            y_max += pad
        else:
            pad = (y_max - y_min) * 0.06
            y_min -= pad
            y_max += pad

        left = 78.0
        top = 54.0
        bottom = float(height - 68)
        legend_width = 220.0 if legend else 28.0
        right = float(width) - legend_width
        plot_width = right - left
        plot_height = bottom - top
        x_span_ns = x_max.value - x_min.value
        y_span = y_max - y_min

        def x_coord(timestamp: pd.Timestamp) -> float:
            ratio = (timestamp.value - x_min.value) / x_span_ns
            return left + ratio * plot_width

        def y_coord(value: float) -> float:
            ratio = (value - y_min) / y_span
            return bottom - ratio * plot_height

        parts = [
            (
                '<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{width}" height="{height}" '
                f'viewBox="0 0 {width} {height}" role="img">'
            ),
            f"<title>{escape(title)}</title>",
            (f'<rect x="0" y="0" width="{width}" height="{height}" fill="white" />'),
            self._text(left, 28, title, size=16, weight="600"),
        ]

        y_ticks = 5
        for index in range(y_ticks):
            ratio = index / (y_ticks - 1)
            value = y_max - ratio * y_span
            y = top + ratio * plot_height
            parts.append(
                self._line(
                    left,
                    y,
                    right,
                    y,
                    stroke="#e5e7eb",
                    opacity=0.9,
                )
            )
            parts.append(
                self._text(
                    left - 10,
                    y + 4,
                    self._format_number(value),
                    size=11,
                    anchor="end",
                )
            )

        x_ticks = 5
        span_seconds = (x_max - x_min).total_seconds()
        for index in range(x_ticks):
            ratio = index / (x_ticks - 1)
            timestamp = x_min + (x_max - x_min) * ratio
            x = left + ratio * plot_width
            parts.append(self._line(x, top, x, bottom, stroke="#f3f4f6"))
            parts.append(
                self._text(
                    x,
                    bottom + 20,
                    self._format_timestamp(timestamp, span_seconds),
                    size=10,
                    anchor="middle",
                )
            )

        parts.extend(
            [
                self._line(
                    left,
                    top,
                    left,
                    bottom,
                    stroke="#111827",
                    width=1.2,
                ),
                self._line(
                    left,
                    bottom,
                    right,
                    bottom,
                    stroke="#111827",
                    width=1.2,
                ),
            ]
        )

        y_label = next(iter(units)) if len(units) == 1 else "Value"
        parts.append(
            self._text(
                20,
                (top + bottom) / 2,
                y_label,
                size=12,
                anchor="middle",
                rotate=-90,
            )
        )
        parts.append(
            self._text(
                (left + right) / 2,
                height - 18,
                "Time (UTC)",
                size=12,
                anchor="middle",
            )
        )

        legend_entries = []

        for series_index, ((metric, source, dataset), group) in enumerate(groups):
            color = _PALETTE[series_index % len(_PALETTE)]
            label = self._series_label(
                metric=str(metric),
                source=str(source),
                dataset=str(dataset),
                include_source=include_source,
                include_dataset=include_dataset,
            )
            legend_entries.append((color, label))
            group = group.sort_values("timestamp")

            if kind == "scatter":
                for _, row in group.iterrows():
                    numeric = self._numeric_value(row["value"])
                    if numeric is None:
                        continue
                    x = x_coord(row["timestamp"])
                    y = y_coord(numeric)
                    parts.append(
                        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.5" fill="{color}" />'
                    )
                continue

            segment = []

            for _, row in group.iterrows():
                numeric = self._numeric_value(row["value"])

                if numeric is None:
                    self._append_line_segment(
                        parts,
                        segment,
                        color,
                    )
                    segment.clear()
                    continue

                segment.append(
                    (
                        x_coord(row["timestamp"]),
                        y_coord(numeric),
                    )
                )

            self._append_line_segment(
                parts,
                segment,
                color,
            )

        if legend:
            legend_x = right + 24
            legend_y = top + 8
            for index, (color, label) in enumerate(legend_entries):
                y = legend_y + index * 24
                parts.append(
                    self._line(
                        legend_x,
                        y,
                        legend_x + 18,
                        y,
                        stroke=color,
                        width=3,
                    )
                )
                parts.append(self._text(legend_x + 26, y + 4, label, size=11))

        parts.append("</svg>")
        return "".join(parts)

    def plot(
        self,
        data: pd.DataFrame,
        *,
        kind: PlotKind = "line",
        fields: str | tuple[str, ...] | list[str] | None = None,
        title: str | None = None,
        legend: bool = True,
        width: int = 900,
        height: int = 480,
    ) -> PlotResult:
        """Render canonical data with Orbitoby's native SVG engine.

        No interpolation, smoothing, resampling, forward-fill,
        or other scientific-value transformation occurs.
        """

        if kind not in {"line", "scatter"}:
            raise ValueError("kind must be 'line' or 'scatter'.")

        frame = self._validate_plot_frame(data)

        if fields is not None:
            if isinstance(fields, str):
                requested = {fields}
            else:
                requested = set(fields)
            frame = frame[frame["metric"].isin(requested)].copy()
            if frame.empty:
                raise ValueError(
                    "None of the requested fields exist in the canonical plot data."
                )

        metrics = list(dict.fromkeys(frame["metric"].astype(str).tolist()))
        if title is None:
            title = (
                metrics[0] if len(metrics) == 1 else "Orbitoby canonical time series"
            )

        svg = self._render_svg(
            frame,
            kind=kind,
            title=title,
            legend=legend,
            width=width,
            height=height,
        )

        return PlotResult(
            svg=svg,
            data=frame,
            provenance=self._provenance_frame(frame),
        )

    def plot_timeseries(
        self,
        metric: str | None = None,
        *,
        fields=None,
        start,
        end,
        source: str | None = None,
        source_preference=None,
        dataset: str | None = None,
        artifact_resolution="all",
        archive_raw: bool = True,
        kind: PlotKind = "line",
        title: str | None = None,
        legend: bool = True,
        width: int = 900,
        height: int = 480,
    ) -> PlotResult:
        """Query canonical research data and render native SVG."""

        frame = self.timeseries(
            metric,
            fields=fields,
            start=start,
            end=end,
            source=source,
            source_preference=source_preference,
            dataset=dataset,
            artifact_resolution=artifact_resolution,
            archive_raw=archive_raw,
        )

        return self.plot(
            frame,
            kind=kind,
            title=title,
            legend=legend,
            width=width,
            height=height,
        )
