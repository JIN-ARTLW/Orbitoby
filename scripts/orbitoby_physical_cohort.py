#!/usr/bin/env python3
"""Export unified three-source physical satellite candidates, optionally joined to local TLE Parquet."""
import argparse
import json
from pathlib import Path
from orbitoby.physical_research import physical_satellites, FIELDS


def main():
    ap = argparse.ArgumentParser(description='Orbitoby physical+TLE cohort; no orbital filters')
    ap.add_argument('--db', default=None, help='3-source SQLite archive folder')
    ap.add_argument('--catalog-csv', default=None, help='Optional all-NORAD reference, otherwise ob.catalog(all)')
    ap.add_argument('--require', action='append', default=[], help='E.g. mass, area, diameter, ballistic')
    ap.add_argument('--tle-parquet', default=None, help='Folder or glob of TLE historical parquet files')
    ap.add_argument('--include-sources', action='store_true', help='Add per-field provenance and alternatives')
    ap.add_argument('--include-nonpayload', action='store_true', help='Include non-payload space objects')
    ap.add_argument('--out', required=True, help='Output directory')
    args = ap.parse_args()
    output = Path(args.out).expanduser()
    output.mkdir(parents=True, exist_ok=True)
    cohort = physical_satellites(path=args.db, catalog=args.catalog_csv, required=args.require,
                                 satellites_only=not args.include_nonpayload,
                                 include_sources=args.include_sources, tle_parquet=args.tle_parquet)
    cohort.to_csv(output / 'physical_satellites_unified.csv')
    (output / 'physical_satellites_manifest.json').write_text(
        json.dumps(cohort.manifest, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print('[UNIVERSE]', cohort.manifest['reference_catalog_norad_ids'])
    print('[SELECTED]', cohort.manifest['selected_norad_ids'])
    print('[REQUIRED]', cohort.manifest['required'])
    if 'tle_join' in cohort.manifest: print('[TLE]', cohort.manifest['tle_join'])
    print('[OUT]', output / 'physical_satellites_unified.csv')
    print('[NOTE] mass is catalog-time; geometric area is NOT drag area; B requires separate evidence')


if __name__ == '__main__': main()
