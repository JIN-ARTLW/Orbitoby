#!/usr/bin/env python3
"""Run official 3-provider physical archives sync and query with Orbitoby."""

import argparse
import csv
import json
from pathlib import Path

from orbitoby.physical_archives import GCAT_DEFAULT, GCAT_FULL, PhysicalArchive


def main():
    p = argparse.ArgumentParser(
        description="GCAT + ESA DISCOS + KeepTrack, no orbit filters"
    )
    p.add_argument(
        "--db",
        default="~/Desktop/Orbitoby_Physical_Archives",
        help="Local DB and compressed raw snapshots",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sync = sub.add_parser(
        "sync", help="Retrieve only official bulk/paginated interfaces"
    )
    sync.add_argument("--gcat", choices=("none", "standard", "all"), default="none")
    sync.add_argument("--discos", choices=("none", "pages"), default="none")
    sync.add_argument("--discos-max-pages", type=int, default=10)
    sync.add_argument("--discos-page-size", type=int, default=100)
    sync.add_argument(
        "--keeptrack",
        action="store_true",
        help="ONE official /v4/sats/brief bulk request",
    )
    sync.add_argument(
        "--keeptrack-approved-file",
        help="Only an officially approved detailed BULK export",
    )
    sync.add_argument("--refresh", action="store_true")
    get = sub.add_parser("get", help="All provider records and their provenance")
    get.add_argument("norad_id", type=int)
    get.add_argument("--provider", choices=("gcat", "discos", "keeptrack"))
    get.add_argument("--no-raw", action="store_true")
    sel = sub.add_parser("select", help="NORAD IDs with all named evidence fields")
    sel.add_argument("--require", action="append", required=True)
    sel.add_argument("--provider", choices=("gcat", "discos", "keeptrack"))
    sel.add_argument("--limit", type=int, default=50)
    exp = sub.add_parser("export", help="Long-form evidence CSV with source fields")
    exp.add_argument("--out", required=True)
    exp.add_argument("--require", action="append", default=[])
    wide = sub.add_parser(
        "export-wide", help="One row per NORAD ID with provider-specific columns"
    )
    wide.add_argument("--out", required=True)
    wide.add_argument("--require", action="append", default=[])
    conflicts = sub.add_parser(
        "conflicts", help="Disagreements only on same physical quantity"
    )
    conflicts.add_argument("--field", required=True)
    conflicts.add_argument("--tolerance", type=float, default=0.05)
    raw = sub.add_parser(
        "find-raw",
        help="Search ANY provider-native raw field, even when not normalized",
    )
    raw.add_argument(
        "--provider", choices=("gcat", "discos", "keeptrack"), required=True
    )
    raw.add_argument("--field", required=True, help="e.g. attributes.mass for DISCOS")
    raw.add_argument("--limit", type=int, default=20)
    audit = sub.add_parser(
        "audit", help="Compare to full Orbitoby catalog; never apply orbit filters"
    )
    audit.add_argument(
        "--catalog-csv",
        help="Optional complete NORAD catalog CSV; defaults to ob.catalog(all)",
    )
    audit.add_argument("--out", help="Store full JSON including missing NORAD IDs")
    sub.add_parser("status", help="Snapshot coverage and collection progress")
    args = p.parse_args()
    with PhysicalArchive.open(args.db) as archive:
        if args.cmd == "sync":
            if args.gcat != "none":
                archive.sync_gcat(
                    catalogs=GCAT_FULL if args.gcat == "all" else GCAT_DEFAULT,
                    refresh=args.refresh,
                )
            if args.discos == "pages":
                archive.sync_discos_pages(
                    max_pages=args.discos_max_pages,
                    page_size=args.discos_page_size,
                    refresh=args.refresh,
                )
            if args.keeptrack:
                archive.sync_keeptrack(refresh=args.refresh)
            if args.keeptrack_approved_file:
                print(
                    "[KeepTrack approved export]",
                    archive.import_authorized_keeptrack_file(
                        args.keeptrack_approved_file
                    ),
                )
            print("[DONE]", json.dumps(archive.sources(), ensure_ascii=False))
        elif args.cmd == "get":
            print(
                json.dumps(
                    archive.get(
                        args.norad_id,
                        provider=args.provider,
                        include_raw=not args.no_raw,
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif args.cmd == "select":
            ids = archive.select(required=args.require, provider=args.provider)
            print(f"Matching NORAD objects: {len(ids):,}")
            print("First matches:", ids[: args.limit])
        elif args.cmd == "export":
            print("[EXPORT]", archive.export_csv(args.out, required=args.require))
        elif args.cmd == "export-wide":
            print("[WIDE]", archive.export_wide(args.out, required=args.require))
        elif args.cmd == "conflicts":
            out = archive.collisions(args.field, relative_tolerance=args.tolerance)
            print(
                json.dumps(
                    {"count": len(out), "first": out[:50]}, ensure_ascii=False, indent=2
                )
            )
        elif args.cmd == "find-raw":
            print(
                json.dumps(
                    archive.find_raw(args.provider, args.field, limit=args.limit),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif args.cmd == "audit":
            if args.catalog_csv:
                with open(
                    Path(args.catalog_csv).expanduser(),
                    newline="",
                    encoding="utf-8-sig",
                ) as f:
                    rows = list(csv.DictReader(f))
                if not rows:
                    raise ValueError("Empty catalog CSV")
                columns = {x.casefold(): x for x in rows[0]}
                key = next(
                    (
                        columns[x]
                        for x in ("norad_id", "norad_cat_id", "satnum")
                        if x in columns
                    ),
                    None,
                )
                if key is None:
                    raise ValueError("Catalog CSV needs norad_id column")
                ids = [row[key] for row in rows]
            else:
                import orbitoby as ob

                df = ob.catalog("all", refresh=False).table
                names = {str(c).casefold(): c for c in df.columns}
                key = next(
                    (
                        names[x]
                        for x in ("norad_id", "norad_cat_id", "satnum")
                        if x in names
                    ),
                    None,
                )
                if key is None:
                    raise ValueError("Orbitoby catalog needs NORAD column")
                ids = df[key].tolist()
            result = archive.audit_universe(ids)
            print("[AUDIT] total", result["reference_norad_count"])
            for provider, val in result["providers"].items():
                print(
                    provider, "matched=", val["matched"], "unmatched=", val["unmatched"]
                )
            if args.out:
                path = Path(args.out).expanduser()
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print("[AUDIT FILE]", path)
        else:
            print(
                "SOURCES", json.dumps(archive.sources(), ensure_ascii=False, indent=2)
            )
            print("STATE", json.dumps(archive.state(), ensure_ascii=False, indent=2))
            print(
                "FIELD COVERAGE",
                json.dumps(archive.coverage(), ensure_ascii=False, indent=2),
            )


if __name__ == "__main__":
    main()
