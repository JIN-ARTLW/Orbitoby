"""Lossless, NORAD-ID-left-join of Orbitoby's plotted objects and GCAT physics.

This script joins *every* distinct NORAD ID in the user plot's monthly TLE output
including IDs missing from GCAT. TLE-derived altitude is not physical size/area.
Optional DISCOS (pre-authorized local CSV) and per-object documented evidence
only enrich fields whose source is known. No values are fabricated or propagated.

Optional provider retrieval via orbitoby.physical_specs (installed in earlier patch).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from orbitoby.physical_specs import (
    attach_discos,
    attach_documented_evidence,
    parse_gcat,
    rank_completeness,
    retrieve_gcat,
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read_universe(plot_dir: Path, *, source_file: Path | None = None) -> tuple[pd.DataFrame, Path]:
    """Build actual *plotted* NORAD universe (not every catalog-only identifier)."""
    source = source_file or (plot_dir / 'satellite_monthly_le550.csv')
    if not source.is_file():
        raise FileNotFoundError(f'Plot object data missing: {source}')
    frame = pd.read_csv(source, low_memory=False)
    id_col = next((c for c in frame if str(c).casefold() in ('norad_id', 'norad_cat_id', 'satnum')), None)
    if id_col is None:
        raise ValueError(f'Missing NORAD ID column in {source}: {list(frame.columns)}')
    ids = pd.to_numeric(frame[id_col], errors='coerce')
    if ids.isna().any() or not ((ids > 0) & (ids < 1_000_000_000)).all() or not (ids % 1 == 0).all():
        raise ValueError('Unparseable/invalid NORAD identifiers in plot output: refuse silent omission')
    frame = frame.copy()
    frame['norad_id'] = ids.astype('int64')
    agg = {'plotted_records': ('norad_id', 'size')}
    if 'epoch' in frame:
        frame['epoch'] = pd.to_datetime(frame['epoch'], errors='coerce', utc=True)
        if frame['epoch'].isna().any():
            raise ValueError('Invalid plot epoch found; cannot audit time span')
        agg['plot_first_epoch'] = ('epoch', 'min')
        agg['plot_last_epoch'] = ('epoch', 'max')
    if 'is_cubesat' in frame:
        # Ambiguity should be logged as catalog classification, not physical truth.
        frame['is_cubesat'] = frame['is_cubesat'].astype(str).str.lower().isin(('true', '1', 'yes'))
        agg['plot_classified_cubesat'] = ('is_cubesat', 'max')
    unique = frame.groupby('norad_id', sort=True, as_index=False).agg(**agg)
    if unique['norad_id'].duplicated().any():
        raise AssertionError('Internal error: duplicate target NORAD ID')
    return unique, source


def read_first_tle_audit(plot_dir: Path, universe: pd.DataFrame) -> tuple[pd.DataFrame, Path | None]:
    p = plot_dir / 'first_tle_altitude_eligibility_audit.csv'
    if not p.exists():
        return universe, None
    aud = pd.read_csv(p, low_memory=False)
    if 'norad_id' not in aud.columns or aud['norad_id'].duplicated().any():
        raise ValueError('First-TLE audit file missing valid unique NORAD identifiers')
    keep = [c for c in (
        'norad_id', 'first_tle_epoch', 'first_alt_km', 'first_mean_motion',
        'first_eccentricity', 'starts_within_altitude_band',
        'historical_tle_rows',
    ) if c in aud.columns]
    out = universe.merge(aud[keep], on='norad_id', how='left', validate='one_to_one')
    return out, p


def load_or_retrieve_gcat(gcat_dir: Path, refresh: bool = False):
    paths, receipts = retrieve_gcat(gcat_dir, refresh=refresh)
    parsed = []
    for p in paths:
        name = p.stem.replace('gcat_', '')
        parsed.append(parse_gcat(p.read_bytes(), catalog_name=name))
    if not parsed:
        raise ValueError('GCAT source list empty')
    cats = pd.concat(parsed, ignore_index=True)
    if 'norad_id' not in cats:
        raise ValueError('GCAT did not contain norad_id')
    # Strictly do not overwrite conflicting physical rows from separate catalogs.
    # Ambiguous identities stay in left join and are marked, not silently dropped.
    multi_ids = cats.loc[cats['norad_id'].duplicated(keep=False), 'norad_id'].drop_duplicates()
    ambiguous = cats[cats['norad_id'].isin(multi_ids)].copy()
    cats = cats[~cats['norad_id'].isin(multi_ids)].copy()
    return cats, ambiguous, receipts


def attach_user_discos(gcat: pd.DataFrame, path: Path | None):
    if path is None:
        return gcat, 0
    e = pd.read_csv(path)
    required = {'norad_id'}
    if not required.issubset(e):
        raise ValueError('DISCOS import must contain norad_id')
    if e.norad_id.duplicated().any():
        raise ValueError('DISCOS export contains duplicate NORAD identifiers')
    return attach_discos(gcat, e), len(e)


def full_left_join(universe: pd.DataFrame, gc: pd.DataFrame, ambiguous_ids: set[int]):
    """Hard cardinality contract: one row per plotted NORAD, NEVER an inner join."""
    if universe['norad_id'].duplicated().any():
        raise ValueError('Universe contains duplicate NORAD IDs')
    if gc['norad_id'].duplicated().any():
        raise ValueError('GCAT contains duplicate NORAD IDs after conflict filtering')
    joined = universe.merge(gc, on='norad_id', how='left', validate='one_to_one', indicator=True,
                            suffixes=('_plot', '_gcat'))
    joined['gcat_match_status'] = joined['_merge'].astype(str).map({'both': 'matched', 'left_only': 'no_gcat_match'})
    joined.loc[joined['norad_id'].isin(ambiguous_ids), 'gcat_match_status'] = 'ambiguous_gcat_norad'
    joined = joined.drop(columns=['_merge'])
    joined['gcat_payload'] = joined['object_type'].fillna('').astype(str).str.startswith('P') if 'object_type' in joined else False
    joined['research_catalog_partial'] = (joined['gcat_match_status'].eq('matched') & joined['gcat_payload'] &
        joined['mass_known'].eq(True) & joined['dimensions_known'].eq(True))
    joined['research_strict_documented'] = (joined['research_catalog_partial'] & joined['strict_documented'].eq(True))
    if len(joined) != len(universe) or joined.norad_id.nunique() != universe.norad_id.nunique():
        raise AssertionError('FULL JOIN cardinality contract failed')
    return joined


def summarize(joined: pd.DataFrame, universe: pd.DataFrame, *, expected_count: int | None):
    n = len(joined)
    if expected_count is not None and n != expected_count:
        raise ValueError(f'Expected exactly {expected_count:,} plotted objects, found {n:,}: '
                         'verify plotting directory/selection before calling this a full merge')
    def n_true(field):
        return int(joined[field].eq(True).sum())

    metrics = {
        'plot_universe_norad_ids': len(universe),
        'output_unique_norad_ids': joined.norad_id.nunique(),
        'gcat_matched': int(joined.gcat_match_status.eq('matched').sum()),
        'gcat_unmatched': int(joined.gcat_match_status.eq('no_gcat_match').sum()),
        'gcat_ambiguous': int(joined.gcat_match_status.eq('ambiguous_gcat_norad').sum()),
        'catalog_mass_reported': n_true('mass_known'),
        'catalog_mass_unflagged': n_true('mass_unflagged'),
        'body_dimensions_reported': n_true('dimensions_known'),
        'panel_status_documented': n_true('panel_documented'),
        'surface_area_documented': n_true('surface_area_documented'),
        'drag_area_documented': n_true('drag_area_documented'),
        'catalog_partial_candidates': n_true('research_catalog_partial'),
        'strict_documented_candidates': n_true('research_strict_documented'),
        'gcat_matched_but_not_payload': int((joined.gcat_match_status.eq('matched') & ~joined.gcat_payload).sum()),
        'unknown_solar_panel_status': int(joined.solar_panel_status.fillna('unknown').eq('unknown').sum()),
    }
    assert metrics['gcat_matched'] + metrics['gcat_unmatched'] + metrics['gcat_ambiguous'] == n
    return metrics


def run(args):
    out = args.out.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    plot_dir = args.plot_dir.expanduser().resolve()
    universe, plot_path = read_universe(plot_dir, source_file=args.universe_csv)
    universe, audit_path = read_first_tle_audit(plot_dir, universe)
    print(f'[UNIVERSE] Exactly {len(universe):,} unique plotted NORAD IDs from {plot_path}', flush=True)
    if args.expected_count is not None and len(universe) != args.expected_count:
        raise ValueError(f'Expected {args.expected_count:,} IDs, found {len(universe):,}; wrong dataset?')
    gc, ambiguous, receipts = load_or_retrieve_gcat(args.gcat_dir.expanduser() if args.gcat_dir else out / 'source_cache', args.refresh_gcat)
    print(f'[GCAT] {len(gc):,} unique records; {ambiguous.norad_id.nunique():,} ambiguous NORAD IDs', flush=True)

    if args.discos_csv:
        gc, imported = attach_user_discos(gc, args.discos_csv.expanduser())
    else:
        imported = 0
    if args.manual_evidence:
        manual = pd.read_csv(args.manual_evidence.expanduser())
        gc = attach_documented_evidence(gc, manual)
    gc = rank_completeness(gc)
    joined = full_left_join(universe, gc, set(ambiguous.norad_id.astype(int)))
    metrics = summarize(joined, universe, expected_count=args.expected_count)
    print('[COVERAGE] ' + ', '.join(f'{k}={v:,}' for k,v in metrics.items()), flush=True)

    primary = out / 'physical_specs_all_plotted_norad_left_join.csv'
    joined.to_csv(primary, index=False)
    joined.loc[joined.gcat_match_status.ne('matched')].to_csv(out / 'physical_specs_unmatched_or_ambiguous.csv', index=False)
    joined.loc[joined.research_catalog_partial].to_csv(
        out / 'physical_specs_catalog_partial_candidates.csv', index=False)
    joined.loc[joined.research_strict_documented].to_csv(out / 'physical_specs_strict_documented_candidates.csv', index=False)
    ambiguous.to_csv(out / 'gcat_ambiguous_source_rows.csv', index=False)
    pd.DataFrame([{'metric': key, 'count': val, 'pct_of_universe': round(val * 100 / max(len(joined), 1), 3)} for key, val in metrics.items()]).to_csv(
        out / 'physical_specs_coverage_report.csv', index=False)

    manifest = {
        'generated_utc': datetime.now(UTC).isoformat(),
        'join_type': 'LEFT ONE-TO-ONE on NORAD ID; retain missing values/objects',
        'plot_universe_path': str(plot_path), 'plot_universe_sha256': sha256(plot_path),
        'first_tle_audit_path': str(audit_path) if audit_path else None,
        'first_tle_audit_sha256': sha256(audit_path) if audit_path else None,
        'expected_count': args.expected_count,
        'counts': metrics,
        'gcat_sources': receipts,
        'discos_local_csv_import_rows': imported,
        'discos_note': 'No bulk DISCOS web requests. Optional explicitly authorized local export only.',
        'manual_documentation_csv': str(args.manual_evidence) if args.manual_evidence else None,
        'warnings': [
            'Matched GCAT metadata are not all complete or directly measured physical parameters.',
            'MassFlag ? marks an estimate; an unflagged mass is not necessarily independently verified.',
            'GCAT Shape/Span do NOT establish solar-panel state, total surface area, or operational drag projected area.',
            'TLE mean motion -> equivalent altitude is approximate; not a precise geometric altitude.',
            'First TLE means first available valid record; may differ from launch conditions.',
            'Strict evidence completeness does not independently validate the contents of external source URLs.',
            'GCAT objects use Type[0] == P for payload, where present; TLE source classification may differ.',
            'Plot universe is the NORAD identifiers actually present in monthly plot CSV, not the full SATCAT registry.',
            'Public GCAT may not cover certain NORAD temporary or analyst objects; mark as unmatched.',
        ],
        'output': str(primary),
    }
    (out / 'physical_specs_full_join_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print('[DONE] ' + str(primary), flush=True)
    return metrics


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plot-dir', type=Path, required=True,
                   help='Orbitoby_low550_aligned_plots directory containing satellite_monthly_le550.csv')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--universe-csv', type=Path, default=None,
                   help='Alternative CSV with NORAD IDs, instead of monthly plot CSV')
    p.add_argument('--gcat-dir', type=Path, default=None, help='Cached GCAT TSV directory')
    p.add_argument('--refresh-gcat', action='store_true')
    p.add_argument('--manual-evidence', type=Path, default=None)
    p.add_argument('--discos-csv', type=Path, default=None, help='Authorized existing local ESA DISCOS export CSV')
    p.add_argument('--expected-count', type=int, default=None)
    args = p.parse_args()
    run(args)


if __name__ == '__main__':
    main()
