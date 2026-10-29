"""NRLMSIS input and model results with explicit lineage."""

import json
from pathlib import Path

import pandas as pd

from orbitoby._easy_result import DataResult, SourceList


class MsisInputsResult(DataResult):
    """Validated forcing inputs, without running the model."""

    def __init__(self, frame, *, trajectory, lineage, driver_source):
        super().__init__(
            frame,
            name="NRLMSIS 2.1 model inputs",
            start=trajectory.start,
            end=trajectory.end,
            source=driver_source,
        )
        self.trajectory = trajectory
        self.lineage = tuple(lineage)
        self.driver_source = driver_source

    def _source_rows(self):
        product = self.trajectory.product.lower()
        satellite = self.trajectory.satellite.lower()

        entries = [
            ("trajectory", "swarm", f"density_{satellite}_{product}"),
            ("F10.7 previous day", self.driver_source, "f107_observed"),
            ("F10.7 centered 81-day", self.driver_source, "f107_observed"),
            ("daily Ap", self.driver_source, "ap_daily"),
            ("3-hour Ap", self.driver_source, "ap"),
        ]
        return pd.DataFrame(entries, columns=["metric", "source", "dataset"])

    def sources(self):
        return SourceList(self._source_rows(), "explicit model inputs")

    def info(self):
        super().info()
        print(
            f"Trajectory: Swarm {self.trajectory.satellite} "
            f"{self.trajectory.product.upper()}"
        )
        print("Model: NRLMSIS 2.1 (not yet calculated)")
        print("F10.7: previous-day and centered 81-day mean")
        print("81-day mean: uses dates after the modeled day")
        print("Ap: daily, current/prior 3-hour and historical averages")
        print("Driver provider:", self.driver_source)
        print("Input lineage records:", len(self.lineage))
        print("Missing forcing: never interpolated or invented")
        return self

    def save(self, filename):
        path = super().save(filename)
        sidecar = path.with_name(path.stem + "_lineage.json")
        sidecar.write_text(
            json.dumps(
                {
                    "role": "model_inputs",
                    "model": "NRLMSIS 2.1",
                    "driver_source": self.driver_source,
                    "trajectory_satellite": self.trajectory.satellite,
                    "trajectory_product": self.trajectory.product,
                    "centered_81day_uses_future_dates": True,
                    "parents": [
                        {
                            "kind": p.parent_kind,
                            "id": p.parent_id,
                            "role": p.role,
                        }
                        for p in self.lineage
                    ],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print("Saved lineage:", sidecar)
        return path


class MsisResult(DataResult):
    """NRLMSIS output, kept separate from observed Swarm density."""

    def __init__(self, frame, *, inputs):
        super().__init__(
            frame,
            name="NRLMSIS modeled neutral mass density",
            start=inputs.start,
            end=inputs.end,
            source="orbitoby",
        )
        self.inputs = inputs
        self.lineage = inputs.lineage

    @property
    def provenance(self):
        return self.table

    def source_dependencies(self):
        """Actual source roles used to construct this model's inputs."""
        return self.inputs._source_rows().copy()

    def sources(self):
        model_row = pd.DataFrame(
            [
                {
                    "metric": "NRLMSIS model output",
                    "source": "orbitoby",
                    "dataset": "nrlmsis_2_1_density",
                }
            ]
        )
        rows = pd.concat(
            [self.inputs._source_rows(), model_row],
            ignore_index=True,
        )
        return SourceList(rows, "model + actual inputs")

    def info(self):
        super().info()
        versions = (
            self._frame["model_version"].dropna().unique().tolist()
            if "model_version" in self._frame
            else []
        )
        print("Data role: model_output (NOT observation)")
        print("Model: NRLMSIS")
        print("Version:", versions)
        print("Driver provider:", self.inputs.driver_source)
        print(
            "Trajectory:",
            f"Swarm {self.inputs.trajectory.satellite}",
            self.inputs.trajectory.product.upper(),
        )
        print("Forcing: previous-day F10.7, centered 81-day F10.7, Ap")
        print("Centered 81-day forcing includes future dates")
        print("Parent lineage records:", len(self.lineage))
        return self

    def save(self, filename):
        path = Path(filename)
        if path.suffix.lower() != ".csv":
            raise ValueError("Use a .csv filename.")

        # Model context remains available in .table, but is not
        # serialized into a shareable CSV by default.
        self.table.drop(columns=["context"], errors="ignore").to_csv(path, index=False)

        sidecar = path.with_name(path.stem + "_lineage.json")
        model_version = (
            self._frame["model_version"].dropna().astype(str).unique().tolist()
            if "model_version" in self._frame
            else []
        )
        sidecar.write_text(
            json.dumps(
                {
                    "role": "model_output",
                    "model": "NRLMSIS",
                    "model_version": model_version,
                    "driver_source": self.inputs.driver_source,
                    "trajectory_satellite": self.inputs.trajectory.satellite,
                    "trajectory_product": self.inputs.trajectory.product,
                    "centered_81day_uses_future_dates": True,
                    "parents": [
                        {
                            "kind": p.parent_kind,
                            "id": p.parent_id,
                            "role": p.role,
                        }
                        for p in self.lineage
                    ],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print("Saved model:", path)
        print("Saved lineage:", sidecar)
        return path
