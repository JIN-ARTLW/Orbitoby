#!/usr/bin/env python3
"""Inventory physical metadata across ALL Orbitoby NORAD objects, without orbit filters.

Research safeguards:
* No TLE/altitude/epoch filters. Universe = Orbitoby catalog('all') or explicit full catalog CSV.
* Left join retains catalog-only NORAD objects, including objects lacking GCAT metadata.
* GCAT Mass is LAUNCH mass; projected drag area and real ballistic coefficient
  cannot be inferred from simple body dimensions / xSectAvg / TLE B*.
* ESA DISCOS only through opt-in *existing authorized CSV*; no token needed.
* Mass, drag area, Cd must be manually documented with source and shared
  configuration_context_id to calculate a documented-input ballistic coefficient.
* Published B with source stays separate from derived B; never substituted silently.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from orbitoby.physical_specs import parse_gcat, retrieve_gcat, rank_completeness

MANUAL_COLS = [
    'norad_id', 'configuration_context_id',
    'mass_kg', 'mass_source_url',
    'drag_projected_area_m2', 'drag_area_source_url',
    'drag_coefficient', 'cd_source_url',
    'published_ballistic_coefficient_kg_m2', 'bc_source_url',
    'surface_area_m2', 'surface_area_source_url',
    'solar_panel_status', 'solar_panel_source_url',
    'attitude_context', 'reference_note',
]
DISCOS_COLS = [
    'norad_id','discos_mass_kg','discos_xsect_avg_m2',
    'discos_xsect_min_m2','discos_xsect_max_m2',
    'discos_shape','discos_source_url'
]

def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def get_col(df, names):
    keys = {str(c).casefold(): c for c in df.columns}
    return next((keys[x.casefold()] for x in names if x.casefold() in keys), None)


def load_universe(*, catalog_csv: Path | None = None):
    if catalog_csv:
        if not catalog_csv.is_file():
            raise FileNotFoundError(catalog_csv)
        raw = pd.read_csv(catalog_csv, low_memory=False)
        src = {'source': 'existing complete Orbitoby catalog CSV',
               'path': str(catalog_csv), 'sha256': sha(catalog_csv)}
    else:
        import orbitoby as ob
        raw = ob.catalog('all', refresh=False).table.copy()
        src = {'source': 'Orbitoby catalog(all, refresh=False)',
               'orbitoby_version': str(getattr(ob,'__version__','unknown'))}
    id_col = get_col(raw, ('norad_id','norad_cat_id','NORAD_CAT_ID','satnum'))
    if id_col is None:
        raise ValueError(f'Catalog has no NORAD column; columns={list(raw.columns)}')
    ids = pd.to_numeric(raw[id_col], errors='coerce')
    valid = ids.notna() & (ids >= 1) & (ids < 1_000_000_000) & ids.eq(ids.round())
    if not valid.all():
        raise ValueError(f'Catalog has {(~valid).sum()} invalid/missing NORAD IDs; refuse silent dropping')
    ids = ids.astype('int64')
    if ids.duplicated().any():
        raise ValueError(f'Catalog has {int(ids.duplicated().sum())} duplicate NORAD IDs')
    df = pd.DataFrame({'norad_id': ids})
    type_col = get_col(raw, ('object_type','OBJECT_TYPE','type'))
    name_col = get_col(raw, ('name','object_name','OBJECT_NAME'))
    df['orbitoby_object_type'] = raw[type_col].astype('string') if type_col else pd.Series(pd.NA, index=raw.index, dtype='string')
    df['orbitoby_object_name'] = raw[name_col].astype('string') if name_col else pd.Series(pd.NA, index=raw.index, dtype='string')
    return df.sort_values('norad_id').reset_index(drop=True), src


def load_gcat(gcat_dir: Path, refresh: bool = False):
    paths, receipts = retrieve_gcat(gcat_dir, refresh=refresh)
    chunks = [parse_gcat(p.read_bytes(), catalog_name=p.stem.removeprefix('gcat_')) for p in paths]
    gc = pd.concat(chunks, ignore_index=True)
    colliding_ids = set(gc.loc[gc.norad_id.duplicated(keep=False), 'norad_id'].astype(int))
    ambiguous = gc[gc.norad_id.isin(colliding_ids)].copy()
    clean = gc[~gc.norad_id.isin(colliding_ids)].copy()
    assert not clean.norad_id.duplicated().any()
    return clean, ambiguous, receipts


def import_discos_csv(path: Path | None):
    if path is None:
        return pd.DataFrame(columns=DISCOS_COLS), None
    df = pd.read_csv(path)
    if 'norad_id' not in df.columns:
        raise ValueError('DISCOS CSV needs norad_id (NORAD satno mapped to this field)')
    df['norad_id'] = pd.to_numeric(df.norad_id, errors='raise').astype('int64')
    if df.norad_id.duplicated().any():
        raise ValueError('DISCOS CSV duplicates NORAD IDs: refuse arbitrary selection')
    for c in DISCOS_COLS:
        if c not in df:
            df[c] = pd.NA
    # Never treat DISCos geometric xSectAvg as verified drag_projected_area.
    return df[DISCOS_COLS].copy(), {'path': str(path), 'sha256': sha(path), 'rows': len(df)}


def import_manual_csv(path: Path | None):
    if path is None:
        return pd.DataFrame(columns=MANUAL_COLS), None
    df = pd.read_csv(path, dtype={'configuration_context_id': 'string'})
    if 'norad_id' not in df:
        raise ValueError('Manual evidence needs norad_id')
    df['norad_id'] = pd.to_numeric(df['norad_id'], errors='raise').astype('int64')
    if df.norad_id.duplicated().any():
        raise ValueError('Manual evidence duplicates NORAD IDs')
    for c in MANUAL_COLS:
        if c not in df:
            df[c] = pd.NA
    for number_col, url_col in (
        ('mass_kg','mass_source_url'), ('drag_projected_area_m2','drag_area_source_url'),
        ('drag_coefficient','cd_source_url'),
        ('published_ballistic_coefficient_kg_m2','bc_source_url'),
        ('surface_area_m2','surface_area_source_url'),
    ):
        values = pd.to_numeric(df[number_col], errors='coerce')
        present = df[number_col].notna() & df[number_col].astype(str).str.strip().ne('')
        if (present & (~values.gt(0) | ~values.apply(math.isfinite))).any():
            raise ValueError(f'Manual {number_col} must be positive finite or blank')
        bad_url = present & ~df[url_col].fillna('').astype(str).str.match(r'^https?://')
        if bad_url.any():
            raise ValueError(f'Manual {number_col} requires source URL ({int(bad_url.sum())} rows)')
        df[number_col] = values
    status = df['solar_panel_status'].fillna('unknown').astype(str).str.strip().str.lower()
    if (~status.isin(['present','absent','unknown'])).any():
        raise ValueError('solar_panel_status must be present/absent/unknown')
    doc = status.isin(['present','absent'])
    if (doc & ~df['solar_panel_source_url'].fillna('').astype(str).str.match(r'^https?://')).any():
        raise ValueError('Documented solar panel status requires source URL')
    df['solar_panel_status'] = status
    return df[MANUAL_COLS].copy(), {'path': str(path), 'sha256': sha(path), 'rows':len(df)}


def build_table(universe, gc, ambiguous, discos, manual):
    """Keep the entire Orbitoby universe; GCAT/DISCOS are independent evidence."""
    if universe.norad_id.duplicated().any() or gc.norad_id.duplicated().any():
        raise ValueError('Nonunique join IDs')
    out = universe.merge(gc, on='norad_id', how='left', indicator=True, validate='one_to_one')
    out['gcat_match_status'] = out.pop('_merge').astype(str).map({'both': 'matched', 'left_only': 'not_found'})
    out.loc[out.norad_id.isin(set(ambiguous.norad_id)), 'gcat_match_status'] = 'ambiguous'

    # GCAT payload indicator is primary; use Orbitoby class only if GCAT is unavailable.
    gc_type = out['object_type'].fillna('').astype(str).str.upper()
    orb_type = out['orbitoby_object_type'].fillna('').astype(str).str.upper()
    out['object_class'] = 'unknown'
    gc_known = gc_type.ne('')
    out.loc[gc_known & gc_type.str.startswith('P'), 'object_class'] = 'payload'
    out.loc[gc_known & ~gc_type.str.startswith('P'), 'object_class'] = 'other_object'
    no_gc_class = ~gc_known
    out.loc[no_gc_class & orb_type.eq('PAYLOAD'), 'object_class'] = 'payload'
    out.loc[no_gc_class & orb_type.isin(['ROCKET BODY','DEBRIS','ROCKET_BODY']), 'object_class'] = 'other_object'

    # Avoid duplicated/old GCAT DISCOS placeholder columns prior to merging external DISCOS values.
    stale_discos = [c for c in out if c.startswith('discos_')]
    out = out.drop(columns=stale_discos)
    discos = discos.copy()
    for c in DISCOS_COLS:
        if c not in discos:
            discos[c] = pd.NA
    out = out.merge(discos[DISCOS_COLS], on='norad_id', how='left', validate='one_to_one')
    out['discos_source_url'] = out['discos_source_url'].where(out['discos_source_url'].notna(), '')
    out['has_discos_catalog_area'] = pd.to_numeric(out['discos_xsect_avg_m2'], errors='coerce').gt(0)

    # GCAT Mass describes mass at launch and should NOT be mistaken for in-orbit m(t).
    out['gcat_mass_available'] = pd.to_numeric(out['launch_mass_kg'], errors='coerce').gt(0)
    out['gcat_mass_unflagged'] = out['gcat_mass_available'] & ~out['launch_mass_flag'].fillna('?').astype(str).str.contains(r'\?')
    out['gcat_body_dimensions_available'] = (
        pd.to_numeric(out['body_length_m'], errors='coerce').gt(0)
        & pd.to_numeric(out['body_diameter_m'], errors='coerce').gt(0)
    )
    # The only geometry inferred automatically: IDEAL SPHERE body reference,
    # not the full deployed spacecraft, not the drag projected area.
    shape = out.get('shape_description', pd.Series('', index=out.index))
    sphere = shape.fillna('').astype(str).str.strip().str.lower().str.match(r'^spher(?:e|ical)(?:\b|$)')
    diameter = pd.to_numeric(out['body_diameter_m'], errors='coerce')
    out['sphere_body_reference_cross_section_m2'] = (math.pi * (diameter / 2) ** 2).where(sphere & diameter.gt(0))
    out['sphere_body_reference_surface_area_m2'] = (math.pi * diameter ** 2).where(sphere & diameter.gt(0))
    out['discos_mass_available'] = pd.to_numeric(out['discos_mass_kg'], errors='coerce').gt(0)
    out['any_mass_reported'] = out['gcat_mass_available'] | out['discos_mass_available']
    geo_area = pd.to_numeric(out['discos_xsect_avg_m2'], errors='coerce')
    geo_area = geo_area.where(geo_area.gt(0))
    out['catalog_m_a_geometry_proxy_kg_m2'] = (
        pd.to_numeric(out['discos_mass_kg'], errors='coerce').combine_first(
            pd.to_numeric(out['launch_mass_kg'], errors='coerce')) / geo_area
    )
    # This is m/A_geo, not m/(Cd A_drag); provenance and units must remain explicit.

    # MANUAL evidence only. Keep it separately, never overwrite GCAT or DISCOS fields.
    man = manual.copy()
    for c in MANUAL_COLS:
        if c not in man:
            man[c] = pd.NA
    man = man[MANUAL_COLS].copy()
    rename_cols = {k: 'verified_' + k for k in MANUAL_COLS if k != 'norad_id'}
    man = man.rename(columns=rename_cols)
    out = out.merge(man, on='norad_id', how='left', validate='one_to_one')
    doc_mass = pd.to_numeric(out['verified_mass_kg'], errors='coerce')
    doc_area = pd.to_numeric(out['verified_drag_projected_area_m2'], errors='coerce')
    doc_cd = pd.to_numeric(out['verified_drag_coefficient'], errors='coerce')
    source_check = (
        out['verified_mass_source_url'].fillna('').astype(str).str.startswith(('https://','http://')) &
        out['verified_drag_area_source_url'].fillna('').astype(str).str.startswith(('https://','http://')) &
        out['verified_cd_source_url'].fillna('').astype(str).str.startswith(('https://','http://'))
    )
    config = out['verified_configuration_context_id'].fillna('').astype(str).str.strip()
    attitude = out['verified_attitude_context'].fillna('').astype(str).str.strip().str.lower()
    possible = (doc_mass.gt(0) & doc_area.gt(0) & doc_cd.gt(0) & source_check & config.ne('')
                & attitude.ne('') & attitude.ne('unknown'))
    out['ballistic_coefficient_computed_kg_m2'] = (doc_mass / (doc_cd * doc_area)).where(possible)
    out['inverse_ballistic_coefficient_computed_m2_kg'] = (1 / out['ballistic_coefficient_computed_kg_m2']).where(possible)
    out['ballistic_coefficient_published_kg_m2'] = pd.to_numeric(
        out['verified_published_ballistic_coefficient_kg_m2'], errors='coerce')
    out['ballistic_coefficient_published_source_url'] = out['verified_bc_source_url']
    out['ballistic_coefficient_available'] = (
        out['ballistic_coefficient_computed_kg_m2'].notna() |
        out['ballistic_coefficient_published_kg_m2'].notna()
    )
    out['has_documented_drag_area'] = doc_area.gt(0)
    out['has_documented_cd'] = doc_cd.gt(0)
    out['has_documented_mass'] = doc_mass.gt(0)
    out['has_documented_surface_area'] = pd.to_numeric(out['verified_surface_area_m2'], errors='coerce').gt(0)
    out['solar_panel_status_documented'] = (
        out['verified_solar_panel_status'].isin(('present','absent')) &
        out['verified_solar_panel_source_url'].fillna('').astype(str).str.startswith(('https://','http://'))
    )
    out['physical_evidence_tier'] = 'D_missing_core_evidence'
    out.loc[out['gcat_mass_available'] & out['gcat_body_dimensions_available'], 'physical_evidence_tier'] = 'C_catalog_mass_dimensions'
    out.loc[out['any_mass_reported'] & out['has_discos_catalog_area'], 'physical_evidence_tier'] = 'B_catalog_geometric_area_proxy'
    out.loc[out['ballistic_coefficient_available'], 'physical_evidence_tier'] = 'A_documented_or_calculable_B'
    if len(out) != len(universe) or out.norad_id.nunique() != len(universe):
        raise AssertionError('Full NORAD catalog cardinality changed during join')
    return out


def write_outputs(joined, universe_receipt, gcat_receipts, discos_receipt, manual_receipt, ambiguous, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        'all': out_dir / 'all_catalog_norad_physical_evidence.csv',
        'payloads': out_dir / 'all_satellite_payloads.csv',
        'mass': out_dir / 'satellites_mass_and_dimensions.csv',
        'geometry': out_dir / 'satellites_mass_plus_catalog_geometric_area.csv',
        'ballistic': out_dir / 'satellites_documented_ballistic_coefficient.csv',
        'followup': out_dir / 'satellites_need_drag_area_or_cd.csv',
        'uncertain': out_dir / 'unresolved_object_class_or_gcat.csv',
        'ambiguity': out_dir / 'gcat_ambiguous_rows.csv',
    }
    joined.to_csv(paths['all'], index=False)
    payloads = joined.loc[joined.object_class.eq('payload')].copy()
    payloads.to_csv(paths['payloads'], index=False)
    payloads.loc[payloads.gcat_mass_available & payloads.gcat_body_dimensions_available].to_csv(paths['mass'], index=False)
    payloads.loc[payloads.any_mass_reported & payloads.has_discos_catalog_area].to_csv(paths['geometry'], index=False)
    payloads.loc[payloads.ballistic_coefficient_available].to_csv(paths['ballistic'], index=False)
    payloads.loc[payloads.any_mass_reported & ~payloads.ballistic_coefficient_available].to_csv(paths['followup'], index=False)
    joined.loc[joined.object_class.eq('unknown') | joined.gcat_match_status.ne('matched')].to_csv(paths['uncertain'], index=False)
    ambiguous.to_csv(paths['ambiguity'], index=False)
    metrics = {
        'entire_orbitoby_catalog_objects': len(joined),
        'classified_payload_satellites': len(payloads),
        'unknown_object_class': int(joined.object_class.eq('unknown').sum()),
        'gcat_matched': int(joined.gcat_match_status.eq('matched').sum()),
        'gcat_unmatched': int(joined.gcat_match_status.eq('not_found').sum()),
        'gcat_ambiguous': int(joined.gcat_match_status.eq('ambiguous').sum()),
        'payloads_gcat_mass': int(payloads.gcat_mass_available.sum()),
        'payloads_gcat_unflagged_mass': int(payloads.gcat_mass_unflagged.sum()),
        'payloads_body_dimensions': int(payloads.gcat_body_dimensions_available.sum()),
        'payloads_spherical_body_reference_area': int(payloads.sphere_body_reference_cross_section_m2.notna().sum()),
        'payloads_mass_plus_body_dimensions': int((payloads.gcat_mass_available & payloads.gcat_body_dimensions_available).sum()),
        'payloads_discos_geometric_area': int(payloads.has_discos_catalog_area.sum()),
        'payloads_mass_plus_geometric_area': int((payloads.any_mass_reported & payloads.has_discos_catalog_area).sum()),
        'payloads_documented_drag_area': int(payloads.has_documented_drag_area.sum()),
        'payloads_documented_cd': int(payloads.has_documented_cd.sum()),
        'payloads_documented_ballistic_coefficient': int(payloads.ballistic_coefficient_available.sum()),
        'payloads_documented_solar_panel_status': int(payloads.solar_panel_status_documented.sum()),
    }
    denominator = max(len(payloads), 1)
    rows = [{'metric': key, 'count': int(value),
             'percent_of_payloads': round(value*100/denominator, 3)} for key,value in metrics.items()]
    (out_dir / 'physical_coverage_report.csv').write_text(pd.DataFrame(rows).to_csv(index=False), encoding='utf-8')
    manifest = {
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'universe': universe_receipt, 'gcat_sources': gcat_receipts,
        'discos_csv': discos_receipt, 'manual_evidence_csv': manual_receipt,
        'counts': metrics,
        'quality_notes': [
            'NO orbital height, TLE history or date filtering was applied.',
            'Only GCAT Type P or Orbitoby PAYLOAD are classified as satellite payloads; unknown class preserved in separate output.',
            'GCAT Mass is mass at launch, not confirmed in-orbit mass; missing estimate flag is not a measurement certificate.',
            'DISCOS xSectAvg/Min/Max are catalog geometric areas, not necessarily instantaneous aerodynamic projected drag area.',
            'Derived sphere cross-sectional and surface area fields are body-only ideal geometry, NOT A_drag or observed measured areas.',
            'catalog_m_a_geometry_proxy_kg_m2 is NOT a physical ballistic coefficient; it omits C_D and attitude.',
            'B = m/(C_D*A_drag) kg/m², inverse B = C_D*A_drag/m m²/kg.',
            'No TLE BSTAR values are used as ballistic coefficients.',
            'Documented BC requires cited published value or contextualized evidence for mass, drag area and C_D.',
            'Tokenless mode: DISCOS data used only if authorized CSV is explicitly provided.',
            'Catalog physical properties do not by themselves establish spacecraft maneuver status.',
        ],
        'output_files': {key: str(path) for key,path in paths.items()},
    }
    (out_dir / 'full_catalog_physical_manifest.json').write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    for key, value in metrics.items():
        print(f'[COVERAGE] {key}={value:,}', flush=True)
    print('[DONE] '+str(paths['all']), flush=True)
    return metrics


def run(args):
    universe, universe_receipt = load_universe(catalog_csv=args.catalog_csv)
    print(f'[UNIVERSE] Complete Orbitoby catalog: {len(universe):,} unique NORAD IDs; no orbit restrictions', flush=True)
    gc, ambiguous, receipts = load_gcat(args.gcat_dir, refresh=args.refresh_gcat)
    print(f'[GCAT] {len(gc):,} unique nonambiguous IDs; {len(ambiguous):,} ambiguous source rows', flush=True)
    discos, disco_receipt = import_discos_csv(args.discos_csv)
    manual, manual_receipt = import_manual_csv(args.manual_evidence)
    if args.discos_csv is None:
        print('[DISCOS] Not supplied: no API token required; geometric area coverage remains unknown.', flush=True)
    result = build_table(universe, gc, ambiguous, discos, manual)
    return write_outputs(result, universe_receipt, receipts, disco_receipt, manual_receipt, ambiguous, args.out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, default=Path.home()/'Desktop'/'Orbitoby_PhysicalSpecs_All_Catalog')
    p.add_argument('--catalog-csv', type=Path, help='Optional complete Orbitoby SATCAT CSV; avoids live/cache catalog lookup')
    p.add_argument('--gcat-dir', type=Path, default=Path.home()/'Desktop'/'Orbitoby_PhysicalSpecs_All_Catalog'/'source_cache')
    p.add_argument('--refresh-gcat', action='store_true')
    p.add_argument('--discos-csv', type=Path, help='Optional prior authorized DISCOS export CSV; NEVER requires a token')
    p.add_argument('--manual-evidence', type=Path, help='Optional per-object mission-document evidence CSV')
    args = p.parse_args()
    run(args)


if __name__ == '__main__':
    main()
