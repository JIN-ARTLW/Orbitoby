"""Create evidence-audited physical-specs CSV for Orbitoby, with optional TLE join."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from orbitoby.physical_specs import (
    attach_discos,
    attach_documented_evidence,
    cohort,
    join_orbit_csv,
    load_gcat,
    query_discos,
    rank_completeness,
    retrieve_gcat,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--gcat-dir",
        type=Path,
        help="Directory with gcat_satcat.tsv and gcat_satcat100k.tsv",
    )
    parser.add_argument("--refresh-gcat", action="store_true")
    parser.add_argument(
        "--manual-evidence", type=Path, help="Optional human-checked documentation CSV"
    )
    parser.add_argument(
        "--discos-ids",
        default="",
        help="Comma-separated NORAD IDs; requires ORBITOBY_DISCOS_TOKEN",
    )
    parser.add_argument(
        "--orbit-csv",
        type=Path,
        help="Optional Orbitoby TLE records/summary CSV to join",
    )
    parser.add_argument(
        "--tier",
        choices=("all", "catalog_physical_partial", "strict_documented"),
        default="catalog_physical_partial",
    )
    parser.add_argument(
        "--include-nonpayload",
        action="store_true",
        help="Include debris/rocket bodies in selection (default payload only)",
    )
    args = parser.parse_args()
    out = args.out.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    cache_dir = args.gcat_dir.expanduser() if args.gcat_dir else out / "source_cache"
    receipts = []
    paths, rec = retrieve_gcat(cache_dir, refresh=args.refresh_gcat)
    receipts.extend(rec)
    frame = load_gcat(paths)

    if args.discos_ids:
        ids = [int(v.strip()) for v in args.discos_ids.split(",") if v.strip()]
        discos, discos_receipts = query_discos(ids)
        frame = attach_discos(frame, discos)
        receipts.extend({"provider": "ESA DISCOS", **r} for r in discos_receipts)
    if args.manual_evidence:
        manual = pd.read_csv(args.manual_evidence, dtype={"norad_id": "int64"})
        frame = attach_documented_evidence(frame, manual)

    frame = rank_completeness(frame)
    frame.to_csv(out / "physical_specs_all.csv", index=False)
    chosen = cohort(frame, min_tier=args.tier, payload_only=not args.include_nonpayload)
    chosen.to_csv(out / "physical_specs_selected.csv", index=False)
    print(
        f"Physical records={len(frame):,}; selected ({args.tier})={len(chosen):,}",
        flush=True,
    )
    print("strict_documented=", int(frame.strict_documented.sum()), flush=True)
    if args.orbit_csv:
        matched = join_orbit_csv(
            frame, args.orbit_csv, strict=(args.tier == "strict_documented")
        )
        if args.tier == "all" or args.include_nonpayload:
            orb = pd.read_csv(args.orbit_csv)
            matched = orb.merge(
                chosen, on="norad_id", how="inner", validate="many_to_one"
            )
        matched.to_csv(out / "orbit_physical_joined.csv", index=False)
        print("Matched TLE rows=", len(matched), flush=True)
    manifest = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "source_receipts": receipts,
        "total_gcat_rows": len(frame),
        "selected_rows": len(chosen),
        "strict_documented_rows": int(frame.strict_documented.sum()),
        "tier": args.tier,
        "payload_only": not args.include_nonpayload,
        "important_limitations": [
            "GCAT launch mass is not necessarily current in-orbit mass.",
            "GCAT dimension/span/shape does not specify attitude-dependent drag area.",
            "DISCOS xSectAvg is a geometric catalog descriptor, not measured A_drag.",
            "Solar-panel status is unknown until supported by a per-object mission-document URL.",
            "strict_documented is evidence completeness only, not calibration of drag coefficient.",
            "Do not commit downloaded raw catalogs or personal ESA tokens.",
        ],
    }
    (out / "physical_specs_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
