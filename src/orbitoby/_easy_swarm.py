"""Beginner-friendly selection of Swarm spacecraft."""


class Swarm:
    """A selected Swarm spacecraft in one research period."""

    def __init__(self, study, satellite):
        if not isinstance(satellite, str):
            raise TypeError("Choose Swarm A, B or C.")

        satellite = satellite.strip().upper()

        if satellite not in {"A", "B", "C"}:
            raise ValueError(
                f"Unknown Swarm spacecraft: {satellite!r}. "
                "Available spacecraft: A, B, C."
            )

        self._study = study
        self.satellite = satellite

    def products(self):
        """List products registered for this spacecraft."""
        adapter = self._study._core.get_source("swarm")
        datasets = tuple(adapter.datasets)
        key = f"_{self.satellite.lower()}_"

        return tuple(dataset for dataset in datasets if key in dataset)

    def density(self, product="pod"):
        """Fetch one Swarm neutral-density product without mixing products."""
        from orbitoby._easy_result import DataResult

        if not isinstance(product, str):
            raise TypeError("product must be 'pod' or 'acc'.")

        product = product.strip().lower()

        if product not in {"pod", "acc"}:
            raise ValueError(
                "Choose product='pod' or product='acc'. "
                "These are different derived data products."
            )

        dataset = f"density_{self.satellite.lower()}_{product}"

        if dataset not in self.products():
            raise ValueError(f"Swarm dataset {dataset!r} is not registered.")

        metric = "thermosphere_neutral_mass_density"

        frame = self._study._core.timeseries(
            metric,
            start=self._study.start,
            end=self._study.end,
            source="swarm",
            dataset=dataset,
            artifact_resolution="all",
        )

        if not frame.empty:
            expected = {
                "metric": metric,
                "source": "swarm",
                "dataset": dataset,
            }

            for column, value in expected.items():
                if column not in frame.columns:
                    raise ValueError(f"Swarm data is missing {column!r}.")

                if not frame[column].eq(value).all():
                    raise ValueError(
                        f"Unexpected {column} in Swarm result. "
                        "Different products must not be mixed."
                    )

        return DataResult(
            frame,
            name=(
                f"Swarm {self.satellite} {product.upper()} "
                "provider-derived neutral density"
            ),
            start=self._study.start,
            end=self._study.end,
            source="swarm",
        )

    def altitude(self, product="pod"):
        """Geodetic altitude from the selected Swarm density product."""
        import math
        from numbers import Real

        import pandas as pd

        from orbitoby._easy_result import DataResult

        density = self.density(product=product)
        frame = density.table

        if frame.empty:
            raise ValueError("No Swarm product records for altitude.")

        if "context" not in frame or "artifact_id" not in frame:
            raise ValueError("Swarm product lacks context or artifact provenance.")

        if frame["artifact_id"].isna().any():
            raise ValueError("Swarm product has missing artifact IDs.")

        def height_m(context):
            if not isinstance(context, dict):
                return None

            value = context.get("Height_GD")

            if isinstance(value, bool) or not isinstance(value, Real):
                return None

            number = float(value)
            return number if math.isfinite(number) else None

        heights = frame["context"].map(height_m)

        if heights.isna().all():
            raise ValueError("No valid Height_GD values in this Swarm product.")

        result = frame.copy()

        # Preserve the parent product's scientific lineage.
        result["parent_metric"] = result["metric"]
        result["parent_transform"] = result.get("transform")
        result["parent_transform_version"] = result.get("transform_version")
        result["parent_artifact_kind"] = result.get("artifact_kind")
        result["parent_quality_flag"] = result.get("quality_flag")

        result["metric"] = "swarm_geodetic_altitude"
        result["value"] = heights / 1000.0
        result["unit"] = "km"
        result["source_value"] = heights
        result["source_field"] = "context.Height_GD"

        result["artifact_kind"] = "orbitoby_derived"
        result["method"] = "Swarm product geodetic height conversion"
        result["transform"] = "orbitoby.height_gd_m_to_km"
        result["transform_version"] = "1"

        result["is_missing"] = heights.isna()
        result["missing_reason"] = heights.map(
            lambda x: "missing_or_invalid_Height_GD" if pd.isna(x) else None
        )

        # Parent quality is retained separately, not misrepresented
        # as a quality assessment of the derived altitude.
        result["quality_flag"] = None

        return DataResult(
            result,
            name=(
                f"Swarm {self.satellite} geodetic altitude ({product.upper()}, derived)"
            ),
            start=self._study.start,
            end=self._study.end,
            source="swarm",
        )

    def trajectory(self, product="pod"):
        """Actual Swarm geodetic trajectory with raw lineage."""
        from orbitoby._easy_trajectory import trajectory_from_density

        density = self.density(product=product)

        return trajectory_from_density(
            density,
            satellite=self.satellite,
            product=product,
        )

    def __repr__(self):
        return f"Swarm {self.satellite} ({self._study.start} to {self._study.end}, UTC)"
