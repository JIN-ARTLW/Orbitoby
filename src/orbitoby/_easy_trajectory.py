"""Swarm geodetic trajectory with explicit parent provenance."""

import json
import math

import pandas as pd

from orbitoby import ProductParent
from orbitoby._easy_result import DataResult, SourceList


class TrajectoryResult(DataResult):
    """Actual geodetic coordinates from a Swarm density product."""

    def __init__(
        self,
        frame,
        *,
        provenance,
        parents,
        satellite,
        product,
        start,
        end,
    ):
        super().__init__(
            frame,
            name=f"Swarm {satellite} {product.upper()} trajectory",
            start=start,
            end=end,
            source="swarm",
        )
        self._provenance = provenance.copy()
        self.parents = tuple(parents)
        self.satellite = satellite
        self.product = product

    @property
    def provenance(self):
        return self._provenance.copy()

    def sources(self):
        return SourceList(self._frame, "swarm")

    def info(self):
        super().info()
        print("Coordinates: geodetic latitude, longitude, altitude")
        print("Altitude: Height_GD / 1000 (metres to kilometres)")
        print("Trajectory source: Swarm density product context")
        print("Original artifacts:", len(self.parents))
        print("Interpolation: none")
        print("Orbit propagation: none")
        return self

    def save(self, filename):
        path = super().save(filename)

        safe_columns = [
            "timestamp",
            "metric",
            "source",
            "dataset",
            "artifact_id",
            "retrieved_at",
            "source_version",
            "quality_flag",
            "artifact_kind",
            "transform",
            "transform_version",
        ]

        columns = [column for column in safe_columns if column in self._provenance]

        provenance_path = path.with_name(path.stem + "_provenance.csv")

        self._provenance[columns].to_csv(
            provenance_path,
            index=False,
        )

        metadata = {
            "satellite": self.satellite,
            "product": self.product,
            "coordinate_system": "geodetic",
            "altitude_unit": "km",
            "altitude_transform": "Height_GD metres / 1000",
            "interpolation": "none",
            "orbit_propagation": "none",
            "parent_artifacts": [
                {
                    "kind": parent.parent_kind,
                    "id": parent.parent_id,
                    "role": parent.role,
                }
                for parent in self.parents
            ],
        }

        metadata_path = path.with_name(path.stem + "_metadata.json")

        metadata_path.write_text(
            json.dumps(
                metadata,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        print("Saved:", path)
        print("Provenance:", provenance_path)
        print("Metadata:", metadata_path)

        return path


def trajectory_from_density(density, *, satellite, product):
    """Extract actual Swarm coordinates without generating samples."""
    frame = density.table.reset_index(drop=True)

    if frame.empty:
        raise ValueError("No Swarm records available for trajectory.")

    required = {"timestamp", "context", "artifact_id"}
    missing = required - set(frame.columns)

    if missing:
        raise ValueError("Swarm trajectory is missing: " + ", ".join(sorted(missing)))

    if frame["artifact_id"].isna().any():
        raise ValueError("Trajectory has missing raw artifact IDs.")

    contexts = frame["context"].tolist()

    if not all(isinstance(value, dict) for value in contexts):
        raise ValueError("Swarm trajectory contains missing or invalid context.")

    coordinates = pd.DataFrame(contexts)

    fields = {
        "longitude_deg": "Longitude_GD",
        "latitude_deg": "Latitude_GD",
        "altitude_km": "Height_GD",
    }

    for native in fields.values():
        if native not in coordinates:
            raise ValueError(f"Swarm trajectory requires context.{native}.")

    trajectory = pd.DataFrame()
    trajectory["timestamp"] = pd.to_datetime(
        frame["timestamp"],
        utc=True,
        errors="raise",
    )

    if trajectory["timestamp"].duplicated().any():
        raise ValueError("Swarm trajectory has duplicate timestamps.")

    for target, native in fields.items():
        numbers = pd.to_numeric(
            coordinates[native],
            errors="raise",
        )

        if (
            numbers.isna().any()
            or not numbers.map(lambda value: math.isfinite(float(value))).all()
        ):
            raise ValueError(f"Swarm trajectory contains invalid {native} values.")

        trajectory[target] = numbers / 1000.0 if target == "altitude_km" else numbers

    if not trajectory["latitude_deg"].between(-90, 90).all():
        raise ValueError("Invalid geodetic latitude.")

    if not trajectory["longitude_deg"].between(-180, 360).all():
        raise ValueError("Invalid geodetic longitude.")

    if (trajectory["altitude_km"] < 0).any():
        raise ValueError("Invalid geodetic altitude.")

    trajectory["metric"] = "swarm_trajectory"
    trajectory["source"] = frame["source"]
    trajectory["dataset"] = frame["dataset"]
    trajectory["artifact_id"] = frame["artifact_id"]

    if "retrieved_at" in frame:
        trajectory["retrieved_at"] = frame["retrieved_at"]

    artifact_ids = sorted({str(value) for value in frame["artifact_id"]})

    parents = tuple(
        ProductParent(
            "raw_artifact",
            artifact_id,
            "trajectory_input",
        )
        for artifact_id in artifact_ids
    )

    return TrajectoryResult(
        trajectory,
        provenance=frame,
        parents=parents,
        satellite=satellite,
        product=product,
        start=density.start,
        end=density.end,
    )
