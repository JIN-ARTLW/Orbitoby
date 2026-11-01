"""Offline, scientific-contract tests for GCAT/DISCOS connectors."""
import math
from pathlib import Path

import pandas as pd
import pytest

from orbitoby.physical_specs import (
    _read_gcat_tsv, attach_discos, attach_documented_evidence,
    cohort, join_orbit_csv, parse_discos_response, parse_gcat,
    rank_completeness,
)

SAMPLE = b'''#JCAT\tSatcat\tType\tName\tMass\tMassFlag\tDryMass\tDryFlag\tLength\tLFlag\tDiameter\tDFlag\tSpan\tSpanFlag\tShape
# Valid synthetic test objects
S0001\t43556\tP\tSYNTHETIC-CUBESAT\t3.1\t?\t2.9\t\t0.30\t\t0.10\t\t0.35\t?\tBox
S0002\t35693\tP\tSYNTHETIC-SPHERE\t27.442\t\t26.5\t\t0.4826\t\t0.4826\t\t0.4826\t\tSphere
S0003\t99999\tD\tUNKNOWN-DEBRIS\t-\t\t-\t\t-\t\t-\t\t-\t\tUnknown
S0004\tA12345\tP\tNO-VALID-NORAD\t10.0\t\t9.0\t\t1.0\t\t0.5\t\t2.0\t\tBox
'''


def test_gcat_parses_real_schema_and_estimate_flags():
    out = parse_gcat(SAMPLE)
    assert set(out.norad_id) == {43556, 35693, 99999}
    r = out.loc[out.norad_id.eq(43556)].iloc[0]
    assert r.launch_mass_kg == pytest.approx(3.1)
    assert r.launch_mass_flag == '?'
    assert r.solar_panel_status == 'unknown'
    assert math.isnan(r.drag_projected_area_m2)
    assert math.isnan(r.surface_area_m2)


def test_discos_geometry_not_promoted_to_drag_area():
    data = {'data': [{'attributes': {'satno': 35693, 'mass': 27.442, 'shape': 'Sphere',
                                     'xSectAvg': 0.183, 'xSectMin': 0.183, 'xSectMax': 0.183}}]}
    r = parse_discos_response(data, 35693)
    assert r['discos_xsect_avg_m2'] == pytest.approx(0.183)
    frame = attach_discos(parse_gcat(SAMPLE), pd.DataFrame([r]))
    row = frame.loc[frame.norad_id.eq(35693)].iloc[0]
    assert math.isnan(row.drag_projected_area_m2)
    assert row.discos_xsect_avg_m2 == pytest.approx(0.183)
    assert not rank_completeness(frame).loc[frame.norad_id.eq(35693), 'strict_documented'].item()


def test_strict_rejects_missing_or_estimated_fields():
    base = parse_gcat(SAMPLE)
    ev = pd.DataFrame([
        {'norad_id': 35693, 'solar_panel_status':'absent', 'solar_panel_source_url':'https://example.org/mission',
         'surface_area_m2': 0.7317, 'surface_area_source_url':'https://example.org/dimensions',
         'drag_projected_area_m2': 0.1829, 'drag_area_source_url':'https://example.org/geometry',
         'attitude_context':'spherical rigid object'},
        {'norad_id': 43556, 'solar_panel_status':'present', 'solar_panel_source_url':'https://example.org/panel',
         'surface_area_m2': 0.5, 'surface_area_source_url':'https://example.org/s',
         'drag_projected_area_m2': 0.02, 'drag_area_source_url':'https://example.org/a',
         'attitude_context':'attitude-controlled'},
    ])
    a = rank_completeness(attach_documented_evidence(base, ev))
    assert set(cohort(a, min_tier='strict_documented').norad_id) == {35693}
    assert set(cohort(a).norad_id) == {43556, 35693}


def test_duplicate_evidence_rejected():
    base = parse_gcat(SAMPLE)
    ev = pd.DataFrame({'norad_id':[35693,35693]})
    with pytest.raises(ValueError, match='missing columns'):
        attach_documented_evidence(base, ev)


def test_join_on_norad_only(tmp_path: Path):
    base = rank_completeness(parse_gcat(SAMPLE))
    csvpath = tmp_path/'orbitoby_orbit_records.csv'
    pd.DataFrame({'norad_id':[35693,35693,77777], 'epoch':['2020-01-01','2020-01-02','2020-01-01'],
                  'altitude_km':[350,348,400]}).to_csv(csvpath, index=False)
    joined = join_orbit_csv(base, csvpath)
    assert len(joined) == 2
    assert set(joined.norad_id) == {35693}


def test_gcat_parser_detects_missing_header():
    with pytest.raises(ValueError, match='header'):
        _read_gcat_tsv(b'not a TSV')
