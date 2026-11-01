"""Synthetic regression coverage of full catalog union and evidence-safe TLE linking."""
import json

import pandas as pd
import pytest

from orbitoby.physical_archives import PhysicalArchive
from orbitoby.physical_research import (
    _join_tle_history,
    query_physical,
)

GCAT = b'''#JCAT\tSatcat\tType\tName\tMass\tMassFlag\tDryMass\tLength\tDiameter\tSpan\tShape
S00001\t35694\tP\tCASTOR\t47.45\t\t42\t0.48\t0.4826\t0.48\tSphere
S00002\t35693\tP\tPOLLUX\t27.442\t?\t25\t0.48\t0.4826\t0.48\tSphere
S00003\t99999\tR\tROCKET\t200\t\t195\t3\t2\t2\tCylinder
'''
DISCOS = {'data': [
    {'id':'9','attributes':{'satno':35694,'mass':48,'xSectAvg':0.183,'xSectMin':0.14,'xSectMax':0.2,'shape':'sphere'}},
    {'id':'10','attributes':{'satno':35693,'mass':30,'xSectAvg':0.185}},
]}
KEEP = [{'SCC_NUM':35694,'mass_kg':46.7,'name':'CASTOR'}, {'SCC_NUM':35693,'mass_kg':27.44}]

@pytest.fixture
def loaded(tmp_path):
    with PhysicalArchive.open(tmp_path/'db') as db:
        db.import_gcat_tsv('satcat.tsv', GCAT)
        db.import_discos_page(DISCOS,group='page_1',url='https://discosweb.esoc.esa.int/api/objects')
        db.import_keeptrack_bulk(KEEP,url='https://api.keeptrack.space/v4/sats/brief')
        yield db


def test_full_catalog_and_easy_union(loaded):
    result = query_physical(loaded, catalog=[35694,35693,99999,12345], required=['mass','area'], satellites_only=True)
    assert set(result.table.norad_id) == {35693,35694}
    r = result.table.set_index('norad_id').loc[35694]
    assert r.mass_kg==48 and r.geometric_area_m2==pytest.approx(.183)
    assert r.mass_definition=='catalog_mass'
    assert result.manifest['reference_catalog_norad_ids']==4
    assert result.manifest['required']==['mass_kg','geometric_area_m2']


def test_any_one_source_counts_mass_without_area(loaded):
    res = query_physical(loaded,catalog=[35694,35693,99999,12345], required=['mass'],satellites_only=False)
    assert set(res.table.norad_id)=={35694,35693,99999}
    assert res.table.set_index('norad_id').loc[99999,'geometric_area_m2_available']==False


def test_sources_and_conflicts_are_not_averaged(loaded):
    res = query_physical(loaded,catalog=[35694],include_sources=True,satellites_only=False)
    row=res.table.iloc[0]
    assert row['mass_kg_source']=='discos'
    assert row['mass_kg_conflict']==False # <5% variation across sources
    evidence=json.loads(row['mass_kg_evidence'])
    assert {x['provider'] for x in evidence}=={'gcat','discos','keeptrack'}
    assert not row['ballistic_coefficient_kg_m2_available']
    assert not row['drag_area_m2_available']
    assert row['rcs_category_available']==False


def test_conflict_flag(loaded):
    # 27.442 vs DISCOS 30 = 8.5% discrepancy; no averaging
    res = query_physical(loaded,catalog=[35693],satellites_only=False)
    assert bool(res.table.iloc[0]['mass_kg_conflict'])


def test_missing_universe_retained_without_requirements(loaded):
    res = query_physical(loaded,catalog=pd.DataFrame({'norad_id':[12345,35694],'object_type':['PAYLOAD','PAYLOAD']}))
    assert len(res.table)==2
    assert not res.table.set_index('norad_id').loc[12345,'mass_kg_available']


def test_invalid_or_duplicate_norad(loaded):
    with pytest.raises(ValueError):query_physical(loaded,catalog=[35694,35694])
    with pytest.raises(ValueError):query_physical(loaded,catalog=['a'])


def test_nonexistent_ballistic_cannot_be_silently_inferred(loaded):
    res=query_physical(loaded,catalog=[35694,35693],required=['mass','ballistic'])
    assert res.table.empty


def test_source_label_is_presentation_option(loaded):
    basic=query_physical(loaded,catalog=[35694],include_sources=False).table
    detailed=query_physical(loaded,catalog=[35694],include_sources=True).table
    assert 'mass_kg_source' not in basic
    assert detailed.iloc[0].mass_kg==basic.iloc[0].mass_kg


def test_tle_parquet_without_orbit_filter(tmp_path):
    duckdb = pytest.importorskip('duckdb')
    source=tmp_path/'tle_2026.parquet'
    con=duckdb.connect()
    con.execute("CREATE TABLE tle AS SELECT * FROM (VALUES (35694, '2020-01-01'), (35694, '2020-02-01'), (35693, '2020-05-01')) AS t(norad_id, epoch)")
    con.execute(f"COPY tle TO '{source}' (FORMAT PARQUET)")
    con.close()
    candidates=pd.DataFrame({'norad_id':[35694,35693,12345],'mass_kg':[48,30,None]})
    out,meta=_join_tle_history(candidates,source)
    assert len(out)==3
    assert int(out.set_index('norad_id').loc[35694,'tle_distinct_epochs'])==2
    assert bool(out.set_index('norad_id').loc[35694,'has_tle_history'])
    assert not bool(out.set_index('norad_id').loc[35693,'has_tle_history'])
    assert int(out.set_index('norad_id').loc[12345,'tle_distinct_epochs'])==0
    assert meta['verified_history_two_distinct_epochs']==1
