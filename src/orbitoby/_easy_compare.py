"""Exact-time comparison without interpolation or implicit statistics."""

import json
from pathlib import Path

import pandas as pd

from orbitoby._easy_result import DataResult, SourceList


class ComparisonResult(DataResult):
    """Two compatible scientific series and their exact-time alignment."""

    def __init__(self, left, right):
        if not isinstance(left, DataResult) or not isinstance(right, DataResult):
            raise TypeError("Compare two Orbitoby data results.")

        if left.start != right.start or left.end != right.end:
            raise ValueError("Comparison requires the same study period.")

        frames = []
        metrics = []
        units = []

        required = {"timestamp", "metric", "value", "unit", "source", "dataset"}

        for label, result in (("left", left), ("right", right)):
            frame = result.table

            if frame.empty:
                raise ValueError(f"{label} result contains no records.")

            missing = required - set(frame.columns)
            if missing:
                raise ValueError(
                    f"{label} result is not a canonical time series: "
                    + ", ".join(sorted(missing))
                )

            metric_names = frame["metric"].dropna().astype(str).unique()
            unit_names = frame["unit"].dropna().astype(str).unique()

            if len(metric_names) != 1 or len(unit_names) != 1:
                raise ValueError(
                    "Compare one physical quantity and one unit per result."
                )

            frame = frame.copy()
            frame["timestamp"] = pd.to_datetime(
                frame["timestamp"], utc=True, errors="raise"
            )

            if frame["timestamp"].duplicated().any():
                raise ValueError(
                    f"{label} result has duplicate timestamps. "
                    "Select one source/product explicitly."
                )

            frame["comparison_side"] = label

            if "artifact_kind" in frame:
                kinds = frame["artifact_kind"].dropna().astype(str).unique()
                if len(kinds) > 1:
                    raise ValueError(
                        "One comparison side contains conflicting data roles."
                    )

            frame["plot_label"] = (
                str(result.name)
                + " ["
                + frame["source"].astype(str)
                + " / "
                + frame["dataset"].astype(str)
                + "]"
            )
            frames.append(frame)
            metrics.append(metric_names[0])
            units.append(unit_names[0])

        shared_labels = set(frames[0]["plot_label"]) & set(frames[1]["plot_label"])

        for index, side in enumerate(("Left", "Right")):
            mask = frames[index]["plot_label"].isin(shared_labels)
            frames[index].loc[mask, "plot_label"] += f" ({side})"

        if metrics[0] != metrics[1]:
            raise ValueError(
                f"Different physical quantities: {metrics}. Use study.align() instead."
            )

        if units[0] != units[1]:
            raise ValueError(
                f"Incompatible units: {units}. No automatic conversion was performed."
            )

        self.left = left
        self.right = right
        self.metric = metrics[0]
        self.unit = units[0]

        left_frame, right_frame = frames

        def alignment_side(frame, name):
            result = frame[["timestamp", "value"]].rename(
                columns={"value": f"{name}_value"}
            )
            result[f"{name}_record_exists"] = True

            valid = pd.to_numeric(frame["value"], errors="coerce").notna()

            if "is_missing" in frame:
                valid = valid & ~frame["is_missing"].fillna(True).astype(bool)

            result[f"{name}_valid"] = valid.to_numpy()
            return result

        aligned = (
            alignment_side(left_frame, "left")
            .merge(
                alignment_side(right_frame, "right"),
                on="timestamp",
                how="outer",
                validate="one_to_one",
            )
            .sort_values("timestamp", kind="stable")
            .reset_index(drop=True)
        )

        for name in ("left", "right"):
            for suffix in ("record_exists", "valid"):
                column = f"{name}_{suffix}"
                aligned[column] = aligned[column].fillna(False).astype(bool)

        aligned["exact_record_match"] = (
            aligned["left_record_exists"] & aligned["right_record_exists"]
        )
        aligned["comparable_values"] = aligned["left_valid"] & aligned["right_valid"]

        self._aligned = aligned

        super().__init__(
            pd.concat(frames, ignore_index=True),
            name=f"{self.metric}: exact-time comparison",
            start=left.start,
            end=left.end,
            source="explicit left/right results",
        )

    @property
    def aligned(self):
        return self._aligned.copy()

    @property
    def provenance(self):
        return self._frame.copy()

    @property
    def presence(self):
        columns = ["timestamp", "left_record_exists", "right_record_exists"]
        return self._aligned[columns].copy()

    def show(self, rows=10):
        if not isinstance(rows, int) or rows < 1:
            raise ValueError("rows must be a positive integer.")

        print(f"Exact-time comparison: {len(self._aligned)} timestamps")
        preview = self._aligned.head(rows)
        try:
            from IPython.display import display
        except ImportError:
            print(preview.to_string(index=False))
        else:
            display(preview)
        return self

    def info(self):
        super().info()
        print("Physical quantity:", self.metric)
        print("Unit:", self.unit)
        print("Left:", self.left.name)
        print("Right:", self.right.name)
        print("Exact matching records:", int(self._aligned["exact_record_match"].sum()))
        print("Both values valid:", int(self._aligned["comparable_values"].sum()))
        print("Alignment: exact timestamp union")
        print("Interpolation: none")
        print("Automatic error/correlation calculation: none")
        return self

    def sources(self):
        tables = [
            self.left.sources().table,
            self.right.sources().table,
        ]
        sources = SourceList(self._frame, "comparison")
        sources._table = (
            pd.concat(tables, ignore_index=True)
            .drop_duplicates()
            .reset_index(drop=True)
        )
        return sources

    def save(self, filename):
        path = Path(filename)
        if path.suffix.lower() != ".csv":
            raise ValueError("Use a .csv filename.")

        self._aligned.to_csv(path, index=False)

        safe_columns = [
            "timestamp",
            "metric",
            "value",
            "unit",
            "source",
            "dataset",
            "artifact_kind",
            "artifact_id",
            "product_id",
            "model_name",
            "model_version",
            "transform",
            "transform_version",
            "comparison_side",
        ]

        columns = [name for name in safe_columns if name in self._frame]

        self._frame[columns].to_csv(
            path.with_name(path.stem + "_provenance.csv"),
            index=False,
        )

        self.sources().table.to_csv(
            path.with_name(path.stem + "_sources.csv"),
            index=False,
        )

        metadata = {
            "metric": self.metric,
            "unit": self.unit,
            "left": self.left.name,
            "right": self.right.name,
            "alignment": "exact UTC timestamp union",
            "interpolation": "none",
            "comparable_values": int(self._aligned["comparable_values"].sum()),
        }

        path.with_name(path.stem + "_metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path
