from __future__ import annotations

import sys
import traceback
from pathlib import Path

import pandas as pd

from orbitoby import Archive

OUTPUT_DIR = Path("/tmp/orbitoby_e2e_svg")
OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


CASES = (
    {
        "name": "NRCan F10.7",
        "source": "nrcan",
        "dataset": "f107_measurements",
        "metric": "f107_observed",
        "start": "2024-05-10T00:00:00Z",
        "end": "2024-05-11T00:00:00Z",
    },
    {
        "name": "GFZ Kp",
        "source": "gfz",
        "dataset": "kp",
        "metric": "kp",
        "start": "2024-05-10T00:00:00Z",
        "end": "2024-05-11T00:00:00Z",
    },
    {
        "name": "SILSO sunspot",
        "source": "silso",
        "dataset": "sunspot_daily",
        "metric": "ssn",
        "start": "2024-05-10T00:00:00Z",
        "end": "2024-05-11T00:00:00Z",
    },
    {
        "name": "Kyoto Dst",
        "source": "wdc_kyoto",
        "dataset": "dst_hourly",
        "metric": "dst",
        "start": "2024-05-10T00:00:00Z",
        "end": "2024-05-11T00:00:00Z",
    },
    {
        "name": "CDAWeb OMNI solar wind",
        "source": "cdaweb",
        "dataset": "omni_hourly",
        "metric": "solar_wind_speed",
        "start": "2024-05-10T00:00:00Z",
        "end": "2024-05-11T00:00:00Z",
    },
    {
        "name": "Swarm ACC density",
        "source": "swarm",
        "dataset": "density_a_acc",
        "metric": "thermosphere_neutral_mass_density",
        "start": "2024-05-10T00:00:00Z",
        "end": "2024-05-10T00:02:00Z",
    },
)


def verify_frame(
    frame: pd.DataFrame,
    *,
    source: str,
    dataset: str,
    metric: str,
) -> None:
    if frame.empty:
        raise AssertionError("ResearchAPI returned no canonical rows.")

    required = {
        "timestamp",
        "metric",
        "value",
        "unit",
        "source",
        "dataset",
        "artifact_id",
        "artifact_kind",
    }

    missing = required - set(frame.columns)

    if missing:
        raise AssertionError("Missing canonical columns: " + ", ".join(sorted(missing)))

    if set(frame["source"]) != {source}:
        raise AssertionError(f"Unexpected source values: {set(frame['source'])}")

    if set(frame["dataset"]) != {dataset}:
        raise AssertionError(f"Unexpected dataset values: {set(frame['dataset'])}")

    if set(frame["metric"]) != {metric}:
        raise AssertionError(f"Unexpected metric values: {set(frame['metric'])}")

    timestamps = pd.to_datetime(
        frame["timestamp"],
        utc=True,
        errors="raise",
    )

    if timestamps.dt.tz is None:
        raise AssertionError("Canonical timestamps are not UTC-aware.")

    if frame["artifact_id"].isna().all():
        raise AssertionError("Canonical result has no raw artifact provenance.")


def verify_artifact_link(
    archive: Archive,
    frame: pd.DataFrame,
    *,
    source: str,
    dataset: str,
) -> int:
    artifacts = archive.artifacts(
        source=source,
        dataset=dataset,
    )

    if artifacts.empty:
        raise AssertionError("No raw artifact was registered.")

    canonical_ids = {str(value) for value in frame["artifact_id"].dropna()}

    stored_ids = {str(value) for value in artifacts["artifact_id"].dropna()}

    if not (canonical_ids & stored_ids):
        raise AssertionError(
            "Canonical artifact_id does not reference a registered raw artifact."
        )

    return len(artifacts)


def run_case(
    archive: Archive,
    case: dict,
) -> None:
    print()
    print("=" * 72)
    print(case["name"])
    print("=" * 72)

    frame = archive.timeseries(
        case["metric"],
        source=case["source"],
        dataset=case["dataset"],
        start=case["start"],
        end=case["end"],
        archive_raw=True,
    )

    verify_frame(
        frame,
        source=case["source"],
        dataset=case["dataset"],
        metric=case["metric"],
    )

    artifact_count = verify_artifact_link(
        archive,
        frame,
        source=case["source"],
        dataset=case["dataset"],
    )

    plot = archive.plot(
        frame,
        kind="line",
        title=case["name"],
    )

    if not (plot.svg.startswith("<svg")):
        raise AssertionError("Native PlotAPI did not produce SVG.")

    output = OUTPUT_DIR / (case["source"] + "_" + case["dataset"] + ".svg")

    plot.save(output)

    methods = (
        frame["method"].dropna().unique().tolist() if "method" in frame.columns else []
    )

    statuses = (
        frame["status"].dropna().unique().tolist() if "status" in frame.columns else []
    )

    print(
        "rows:       ",
        len(frame),
    )
    print(
        "time:       ",
        frame["timestamp"].min(),
        "→",
        frame["timestamp"].max(),
    )
    print(
        "unit:       ",
        frame["unit"].dropna().unique().tolist(),
    )
    print(
        "status:     ",
        statuses,
    )
    print(
        "artifact:   ",
        frame["artifact_kind"].dropna().unique().tolist(),
    )
    print(
        "method:     ",
        methods,
    )
    print(
        "raw count:  ",
        artifact_count,
    )
    print(
        "svg:        ",
        output,
    )
    print("PASS")


def main() -> int:
    failures = []

    with Archive() as archive:
        print("Orbitoby live E2E smoke")
        print(
            "sources:",
            ", ".join(sorted(archive.sources_available())),
        )

        for case in CASES:
            try:
                run_case(
                    archive,
                    case,
                )

            except Exception as exc:  # noqa: BLE001
                failures.append(
                    (
                        case["name"],
                        exc,
                    )
                )

                print()
                print(
                    "FAIL:",
                    case["name"],
                )
                print(
                    type(exc).__name__ + ":",
                    exc,
                )

                traceback.print_exc()

    print()
    print("=" * 72)

    if failures:
        print(f"E2E FAILED: {len(failures)} / {len(CASES)}")

        for name, exc in failures:
            print(
                "-",
                name,
                ":",
                type(exc).__name__,
                exc,
            )

        return 1

    print(f"E2E ALL GREEN: {len(CASES)} / {len(CASES)}")

    print(
        "SVG output:",
        OUTPUT_DIR,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
