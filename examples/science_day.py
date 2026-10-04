"""Research stages with explicit sources and exact observed/model comparison.

Run from the repository: .venv/bin/python examples/science_day.py --allow-dotenv
Each failed or unavailable stage is reported separately; exit 1 means incomplete.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from orbitoby import Archive, ProductParent
from orbitoby.auth import CredentialManager

START, END = "2024-05-10", "2024-05-11"
METRIC = "thermosphere_neutral_mass_density"


def population(archive):
    # Full SATCAT, including decayed objects; not today's active GP catalogue.
    archive.fetch(source="celestrak", dataset="satcat", all=True)
    rows = archive.objects(
        start=START, end=END, existence="throughout", object_type="payload"
    )
    if rows.empty:
        raise ValueError("empty period population")
    return rows


def historical(archive, candidates):
    # Explicit demonstration object; no thousands-of-objects provider request.
    selected = candidates[candidates["norad_id"] == 39452]  # Swarm A
    if selected.empty:
        raise ValueError("Swarm A absent from period population")
    rows = archive.orbit(norad_id=39452, start=START, end=END)
    if rows.empty or rows["artifact_id"].isna().any():
        raise ValueError("missing historical orbit/provenance")
    summary = archive.orbit_summary(
        selected,
        start=START,
        end=END,
        periapsis_km=(200, 2000),
        orbit_match="all",
        sync=False,
    )
    if not summary["matches"].all():
        raise ValueError("historical orbit screening failed")
    return summary


def density_comparison(archive):
    observed = archive.timeseries(
        METRIC, source="swarm", dataset="density_a_pod", start=START, end=END
    )
    if observed.empty or observed["artifact_id"].isna().any():
        raise ValueError("missing observed density/provenance")
    # Provider geodetic height is metres; MSIS explicitly requires kilometres.
    context = pd.DataFrame(observed["context"].tolist())
    trajectory = pd.DataFrame(
        {
            "timestamp": observed["timestamp"],
            "longitude_deg": context["Longitude_GD"],
            "latitude_deg": context["Latitude_GD"],
            "altitude_km": context["Height_GD"] / 1000.0,
        }
    )
    parents = [
        ProductParent("raw_artifact", str(value), "trajectory_input")
        for value in observed["artifact_id"].unique()
    ]
    inputs, lineage = archive.msis_inputs(
        trajectory, driver_source="gfz", trajectory_parents=parents
    )
    modeled = archive.msis_density(inputs, parents=lineage)
    if set(modeled["artifact_kind"]) != {"model_output"}:
        raise ValueError("model output separation lost")
    # Retain both sets of provenance, quality and missingness columns.
    comparison = observed.merge(
        modeled,
        on="timestamp",
        how="outer",
        suffixes=("_observed", "_model"),
        validate="one_to_one",
        indicator=True,
    )
    if not comparison["_merge"].eq("both").all():
        raise ValueError("unmatched exact timestamps")
    for product_id in modeled["product_id"].unique():
        if not archive.product_store.lineage(product_id):
            raise ValueError("missing model lineage")
    # Exact matching does not imply every density is valid for analysis.
    print(
        f"  exact_matches={len(comparison)} observed_missing={observed['is_missing'].sum()} model_missing={modeled['is_missing'].sum()}"
    )
    return comparison


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-dotenv", action="store_true")
    parser.add_argument(
        "--output", type=Path, default=Path("/tmp/orbitoby-science-day")
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manager = CredentialManager(
        allow_dotenv=args.allow_dotenv,
        dotenv_path=Path(__file__).resolve().parents[1] / ".env",
    )
    report = {}
    with Archive(credentials=manager) as archive:

        def stage(name, call):
            try:
                frame = call()
                if frame.empty:
                    raise ValueError("empty result")
                frame.to_json(
                    args.output / f"{name}.jsonl",
                    orient="records",
                    lines=True,
                    date_format="iso",
                    double_precision=15,
                )
                report[name] = {"status": "PASS", "rows": len(frame)}
                print(f"PASS {name}: {len(frame)} rows", flush=True)
                return frame
            except Exception as exc:  # noqa: BLE001
                # Exception type only; provider URLs/bodies may contain secrets.
                report[name] = {"status": "FAIL", "error_type": type(exc).__name__}
                print(f"FAIL {name}: {type(exc).__name__}", flush=True)
                return None

        candidates = stage("population", lambda: population(archive))
        if candidates is not None:
            stage("historical_orbit", lambda: historical(archive, candidates))
        else:
            report["historical_orbit"] = {
                "status": "SKIP",
                "reason": "population prerequisite failed",
            }
        for metric, source, dataset in (
            ("f107_observed", "gfz", "f107_observed"),
            ("kp", "gfz", "kp"),
            ("ap", "gfz", "ap"),
            ("ap_daily", "gfz", "ap_daily"),
            ("dst", "wdc_kyoto", "dst_hourly"),
            ("solar_wind_speed", "cdaweb", "omni_hourly"),
        ):
            stage(
                metric,
                lambda m=metric, s=source, d=dataset: archive.timeseries(
                    m, source=s, dataset=d, start=START, end=END
                ),
            )
        stage("density_comparison", lambda: density_comparison(archive))
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return int(any(row["status"] != "PASS" for row in report.values()))


if __name__ == "__main__":
    raise SystemExit(main())
