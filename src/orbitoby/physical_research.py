"""Unified, source-aware physical satellite catalog and optional TLE history link.

No implicit aerodynamic drag-area, drag coefficient, or ballistic coefficient
is inferred from geometric area, RCS, BSTAR, or body dimensions.
"""
from __future__ import annotations

import glob
import json
import math
from dataclasses import dataclass
from pathlib import Path

# Ordered only to make beginner-mode selection deterministic. Scientific
# accuracy is NOT implied by this order; see candidate provenance.
FIELDS = {
    'mass_kg': (('discos', 'catalog_mass_kg'), ('gcat', 'launch_mass_kg'), ('keeptrack', 'reported_mass_kg')),
    'dry_mass_kg': (('gcat', 'dry_mass_kg'), ('keeptrack', 'reported_dry_mass_kg')),
    'geometric_area_m2': (('discos', 'cross_section_geo_avg_m2'),),
    'geometric_area_min_m2': (('discos', 'cross_section_geo_min_m2'),),
    'geometric_area_max_m2': (('discos', 'cross_section_geo_max_m2'),),
    'diameter_m': (('discos', 'body_diameter_m'), ('gcat', 'body_diameter_m'), ('keeptrack', 'reported_diameter_m')),
    'length_m': (('gcat', 'body_length_m'), ('keeptrack', 'reported_length_m')),
    'span_m': (('discos', 'body_span_m'), ('gcat', 'body_span_m'), ('keeptrack', 'reported_span_m')),
    'shape': (('discos', 'shape'), ('gcat', 'shape')),
    'rcs_category': (('keeptrack', 'rcs_category'),),
    # These are only exposed if a future adapter imports EXPLICIT evidence.
    # Neither B* nor xSectAvg nor RCS is accepted as a substitute.
    'drag_area_m2': (('discos', 'documented_drag_area_m2'), ('keeptrack', 'documented_drag_area_m2'), ('gcat', 'documented_drag_area_m2')),
    'drag_coefficient': (('discos', 'documented_cd'), ('keeptrack', 'documented_cd'), ('gcat', 'documented_cd')),
    'ballistic_coefficient_kg_m2': (('discos', 'documented_ballistic_coefficient_kg_m2'), ('keeptrack', 'documented_ballistic_coefficient_kg_m2'), ('gcat', 'documented_ballistic_coefficient_kg_m2')),
    'solar_panel_status': (('discos', 'documented_solar_panel_status'), ('keeptrack', 'documented_solar_panel_status'), ('gcat', 'documented_solar_panel_status')),
}
ALIASES = {
    'mass': 'mass_kg', 'mass_kg': 'mass_kg', 'dry_mass': 'dry_mass_kg',
    'area': 'geometric_area_m2', 'geometric_area': 'geometric_area_m2',
    'cross_section': 'geometric_area_m2', 'cross_section_geo_avg_m2': 'geometric_area_m2',
    'drag_area': 'drag_area_m2', 'cd': 'drag_coefficient',
    'ballistic': 'ballistic_coefficient_kg_m2', 'ballistic_coefficient': 'ballistic_coefficient_kg_m2',
    'diameter': 'diameter_m', 'length': 'length_m', 'span': 'span_m',
    'panel': 'solar_panel_status', 'solar_panel': 'solar_panel_status',
}
NUMERIC = {k for k in FIELDS if k not in {'shape', 'rcs_category', 'solar_panel_status'}}
RAW_SET = {(source, field): normalized for normalized, items in FIELDS.items() for source, field in items}


def _canonical(name):
    key = str(name).strip().lower()
    key = ALIASES.get(key, key)
    if key not in FIELDS:
        raise ValueError(f'Unknown physical field: {name!r}; supported: {sorted(FIELDS)}')
    return key


def _parse_required(fields):
    if isinstance(fields, str):
        fields = (fields,)
    return tuple(dict.fromkeys(map(_canonical, fields)))


def _number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) and n > 0 else None
    except (TypeError, ValueError):
        return None


def _norad(v):
    try:
        if isinstance(v, bool) or str(v).strip() == '': return None
        n = int(str(v).strip())
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def _reference_catalog(catalog):
    """Accept pandas DataFrame, CSV, iterable of IDs, or live ob.catalog('all')."""
    import pandas as pd
    if catalog is None:
        import orbitoby as ob
        if not hasattr(ob, 'catalog'):
            raise RuntimeError('Orbitoby catalog() is unavailable. Supply catalog=CSV/DataFrame/IDs')
        cat = ob.catalog('all', refresh=False)
        df = cat.table if hasattr(cat, 'table') else cat
    elif isinstance(catalog, (str, Path)):
        df = pd.read_csv(Path(catalog).expanduser())
    elif hasattr(catalog, 'columns'):
        df = catalog.copy()
    else:
        df = pd.DataFrame({'norad_id': list(catalog)})
    low = {str(c).strip().lower(): c for c in df.columns}
    key = next((low.get(k) for k in ('norad_id', 'norad_cat_id', 'satnum', 'satno')), None)
    if key is None:
        raise ValueError('Catalog requires NORAD ID (norad_id/norad_cat_id/satnum)')
    nums = df[key].map(_norad)
    if nums.isna().any(): raise ValueError('Invalid NORAD IDs in catalog; refusing silent removal')
    if nums.duplicated().any(): raise ValueError('Duplicated NORAD IDs in catalog')
    out = pd.DataFrame({'norad_id': nums.astype('int64')})
    cl = next((low.get(k) for k in ('object_type','type','orbitoby_object_type')), None)
    out['catalog_object_type'] = df[cl].astype('string').reset_index(drop=True) if cl else pd.NA
    name = next((low.get(k) for k in ('object_name','name')), None)
    out['object_name'] = df[name].astype('string').reset_index(drop=True) if name else pd.NA
    return out


@dataclass
class PhysicalPopulation:
    table: object  # pandas.DataFrame
    manifest: dict

    def to_csv(self, path):
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        self.table.to_csv(p, index=False)
        return p

    def summary(self):
        return self.manifest


def query_physical(archive, *, catalog=None, required=(), satellites_only=True,
                   include_sources=False, tle_parquet=None, conflict_tolerance=0.05):
    """Beginner-mode union of three providers, joined by NORAD to ALL Orbitoby IDs.

    required: mass/area/diameter/... each may be satisfied by ANY source.
    Source priority controls stable presentation only, not evidence confidence.
    If a source differs >5%, a conflict flag is recorded; no averaging.
    All values are per-object catalog metadata, not epoch-matched state.
    """
    import pandas as pd
    if not 0 <= conflict_tolerance <= 1: raise ValueError('conflict_tolerance outside [0,1]')
    req = _parse_required(required)
    df = _reference_catalog(catalog)
    ids = {int(n) for n in df['norad_id']}
    vals = {}
    gcat_type = {}
    # DB-side filtering by field avoids reading all raw GCAT source rows.
    raw_fields = sorted({field for _, field in RAW_SET} | {'object_type'})
    qmarks = ','.join('?' for _ in raw_fields)
    for r in archive.con.execute(
        f'''SELECT norad_id,provider,source_key,field,value_numeric,value_text,unit,caveat
            FROM properties WHERE norad_id IS NOT NULL AND field IN ({qmarks})
            ORDER BY norad_id,provider,field,source_key''', raw_fields):
        n = int(r['norad_id'])
        if n not in ids: continue
        if r['field'] == 'object_type' and r['provider'] == 'gcat':
            t = str(r['value_text'] or '').strip().upper()
            if t and (n not in gcat_type or t.startswith('P')):
                gcat_type[n] = t
        normalized = RAW_SET.get((r['provider'], r['field']))
        if normalized is None: continue
        if normalized in NUMERIC:
            value = _number(r['value_numeric'])
        else:
            value = str(r['value_text']).strip() if r['value_text'] is not None else None
            if value in ('', '-', '?', 'None', 'unknown'): value = None
        if value is None: continue
        vals.setdefault(n, {}).setdefault(normalized, []).append({
            'value': value, 'provider': r['provider'], 'source_key': r['source_key'],
            'source_field': r['field'], 'unit': r['unit'], 'caveat': r['caveat'],
        })
    selected = []
    for row in df.itertuples(index=False):
        n = int(row.norad_id)
        t = str(row.catalog_object_type).strip().upper()
        if t in ('<NA>', 'NAN', 'NONE', ''): t = gcat_type.get(n, '')
        if satellites_only and not (t == 'PAYLOAD' or t.startswith('P ') or t == 'P' or
                                    (t.startswith('P') and not t.startswith('PLATFORM'))):
                continue
        info = vals.get(n, {})
        if any(field not in info for field in req): continue
        result = {'norad_id': n, 'object_name': row.object_name,
                  'object_type': t or None}
        for field, preferences in FIELDS.items():
            options = info.get(field, [])
            ordering = {src: i for i, (src, _) in enumerate(preferences)}
            options.sort(key=lambda z: (ordering.get(z['provider'], 100), z['source_key']))
            result[field] = options[0]['value'] if options else None
            result[field+'_available'] = bool(options)
            if field in NUMERIC:
                nums = [c['value'] for c in options]
                # Same NORAD may have multiple records, including phased objects;
                # mark for review rather than treating duplicates as independent.
                result[field+'_conflict'] = bool(len(nums) > 1 and (max(nums)-min(nums))/max(nums) > conflict_tolerance)
            if include_sources:
                result[field+'_source'] = options[0]['provider'] if options else None
                result[field+'_evidence'] = json.dumps(options, ensure_ascii=False, sort_keys=True) if options else None
        # Do not infer that published geometric area = aerodynamic area.
        result['mass_definition'] = ({'discos': 'catalog_mass', 'gcat': 'launch_mass',
                'keeptrack': 'reported_mass_epoch_unspecified'}.get(
                    info.get('mass_kg', [{}])[0].get('provider')) if info.get('mass_kg') else None)
        result['has_source_conflict'] = any(result.get(k+'_conflict', False) for k in NUMERIC)
        selected.append(result)
    out = pd.DataFrame(selected)
    if out.empty:
        out = pd.DataFrame(columns=['norad_id','object_name','object_type',*FIELDS])
    else:
        out = out.sort_values('norad_id').reset_index(drop=True)
    manifest = {
        'reference_catalog_norad_ids': len(ids),
        'selected_norad_ids': len(out),
        'required': list(req),
        'satellites_only': bool(satellites_only),
        'sources_mode': 'any-one-of-GCAT-DISCOS-KeepTrack',
        'provenance_included_in_csv': bool(include_sources),
        'tie_breaker': 'deterministic field-specific source ordering; NOT scientific quality ranking',
        'conflicts': 'flagged, not averaged',
        'physical_limitations': [
          'catalog mass is NOT confirmed operational mass at TLE epoch',
          'geometric_area_m2 is NOT aerodynamic effective drag area',
          'RCS and BSTAR are NOT aerodynamic area or ballistic coefficient',
          'drag area, Cd and ballistic coefficient require explicit documentary evidence',
        ],
        'source_status': archive.sources(),
        'collection_state': archive.state(),
    }
    if tle_parquet is not None:
        out, orbital = _join_tle_history(out, tle_parquet)
        manifest['tle_join'] = orbital
    return PhysicalPopulation(out, manifest)


def _join_tle_history(df, spec):
    """Read only NORAD+epoch columns in DuckDB; don't materialize full raw TLE.

    No orbit selection; every physical candidate remains even without TLE.
    """
    try:
        import duckdb
    except ImportError as e:
        raise ImportError('Install duckdb to use tle_parquet= (pip install duckdb)') from e
    pat = str(Path(spec).expanduser())
    p = Path(pat)
    if p.is_dir(): files = sorted(map(str, p.glob('*.parquet')))
    else: files = sorted(glob.glob(pat))
    if not files: raise FileNotFoundError('No TLE .parquet files found for '+pat)
    con = duckdb.connect()
    try:
        con.register('physical_candidate_ids', df[['norad_id']])
        con.execute('SELECT * FROM read_parquet(?, union_by_name=true) LIMIT 0', [files])
        cols = {col[0].lower(): col[0] for col in con.description}
        idc = next((cols[k] for k in ('norad_id','norad_cat_id','satnum','satno') if k in cols), None)
        epc = next((cols[k] for k in ('epoch','epoch_utc','timestamp','observed_at') if k in cols), None)
        if not idc or not epc:
            raise ValueError(f'TLE parquet must include NORAD and epoch fields; available={sorted(cols)}')
        quote = lambda col: '"'+col.replace('"','""')+'"'
        sql = f'''SELECT CAST(h.{quote(idc)} AS BIGINT) AS norad_id,
                  COUNT(DISTINCT TRY_CAST(h.{quote(epc)} AS TIMESTAMP)) AS tle_distinct_epochs,
                  MIN(TRY_CAST(h.{quote(epc)} AS TIMESTAMP)) AS tle_first_epoch_utc,
                  MAX(TRY_CAST(h.{quote(epc)} AS TIMESTAMP)) AS tle_last_epoch_utc
                  FROM read_parquet(?, union_by_name=true) h
                  INNER JOIN physical_candidate_ids ids
                    ON TRY_CAST(h.{quote(idc)} AS BIGINT)=ids.norad_id
                  WHERE TRY_CAST(h.{quote(epc)} AS TIMESTAMP) IS NOT NULL
                  GROUP BY 1'''
        matches = con.execute(sql, [files]).df()
    finally:
        con.close()
    merged = df.merge(matches, on='norad_id', how='left', validate='one_to_one')
    merged['tle_distinct_epochs'] = merged['tle_distinct_epochs'].fillna(0).astype('int64')
    merged['has_tle_history'] = merged['tle_distinct_epochs'].ge(2)
    return merged, {'parquet_files': len(files), 'matched_any_epoch': int(merged.tle_distinct_epochs.gt(0).sum()),
                    'verified_history_two_distinct_epochs': int(merged.has_tle_history.sum()),
                    'missing_from_tle': int(merged.tle_distinct_epochs.eq(0).sum()),
                    'no_altitude_or_orbit_filters': True}


def physical_satellites(*, path=None, **kwargs):
    """Simple Orbitoby API: `ob.physical_satellites(required=['mass','area'])`."""
    from .physical_archives import PhysicalArchive
    with PhysicalArchive.open(path) as archive:
        return query_physical(archive, **kwargs)
