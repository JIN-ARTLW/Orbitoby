import json

import pytest

from orbitoby.physical_archives import (
    KEEPTRACK_BULK,
    ArchiveError,
    PhysicalArchive,
)

GCAT_SAMPLE = b"""#JCAT\tSatcat\tType\tName\tMass\tMassFlag\tDryMass\tLength\tDiameter\tSpan\tShape
S00001\t35694\tP\tCASTOR\t47.45\t\t42\t0.48\t0.4826\t0.48\tSphere
S00002\t35693\tP\tPOLLUX\t27.442\t?\t25\t0.48\t0.4826\t0.48\tSphere
"""
GCAT_PAYLOAD = b"""#JCAT\tSatcat\tName\tCategory
S00001\t-\tCASTOR\tTEST
S00002\t-\tPOLLUX\tTEST
"""
DISCOS_SAMPLE = {
    "data": [
        {
            "id": "33",
            "type": "objects",
            "attributes": {
                "satno": 35694,
                "mass": 47.45,
                "xSectAvg": 0.18,
                "xSectMin": 0.14,
                "xSectMax": 0.22,
                "shape": "sphere",
            },
        },
        {
            "id": "34",
            "type": "objects",
            "attributes": {"satno": 35693, "mass": 29.0, "xSectAvg": 0.19},
        },
    ]
}
KT_SAMPLE = [
    {
        "SCC_NUM": 35694,
        "OBJECT_NAME": "CASTOR",
        "RCS": "SMALL",
        "BSTAR": 0.2,
        "EXTRA_PHYSICAL": "original",
    },
    {"SCC_NUM": 35693, "OBJECT_NAME": "POLLUX", "RCS": "MEDIUM"},
]


@pytest.fixture
def archive(tmp_path):
    with PhysicalArchive.open(tmp_path) as db:
        yield db


def test_gcat_full_raw_flags_and_jcat_link(archive):
    assert archive.import_gcat_tsv("satcat.tsv", GCAT_SAMPLE) == 2
    assert archive.import_gcat_tsv("psatcat.tsv", GCAT_PAYLOAD) == 2
    got = archive.get(35694)
    assert len(got["records"]) == 2
    assert any(
        p["field"] == "mass_flag" and p["value_text"] == "?"
        for p in archive.get(35693)["properties"]
    )
    assert any(r["raw"].get("Category") == "TEST" for r in got["records"])


def test_discos_geometry_not_drag(archive):
    archive.import_discos_page(
        DISCOS_SAMPLE, group="page_1", url="https://discosweb.esoc.esa.int/api/objects"
    )
    got = archive.get(35694)
    assert any(
        p["field"] == "cross_section_geo_avg_m2" and p["value_numeric"] == 0.18
        for p in got["properties"]
    )
    assert not any(
        "drag_area" in p["field"] or p["field"] == "ballistic_coefficient_kg_m2"
        for p in got["properties"]
    )


def test_keeptrack_bulk_raw_and_rcs_no_area(archive):
    n, m = archive.import_keeptrack_bulk(KT_SAMPLE)
    assert (n, m) == (2, 2)
    assert archive.raw(35694, "keeptrack")[0]["EXTRA_PHYSICAL"] == "original"
    assert not any(
        p["field"] == "cross_section_geo_avg_m2"
        for p in archive.get(35694)["properties"]
    )


def test_integrated_query_and_disagreement(archive):
    archive.import_gcat_tsv("satcat.tsv", GCAT_SAMPLE)
    archive.import_discos_page(
        DISCOS_SAMPLE, group="one", url="https://discosweb.esoc.esa.int/api/objects"
    )
    archive.import_keeptrack_bulk(KT_SAMPLE)
    assert archive.select(required=["launch_mass_kg", "cross_section_geo_avg_m2"]) == [
        35693,
        35694,
    ]
    assert len(archive.get(35694)["records"]) == 3
    assert archive.select(required=["ballistic_coefficient_kg_m2"]) == []
    assert (
        archive.collisions("catalog_mass_kg") == []
    )  # do not compare launch mass and catalog mass as identical semantics
    assert len(archive.coverage()) > 3


def test_discos_resumes_and_completes(archive, monkeypatch):
    monkeypatch.setenv("ORBITOBY_DISCOS_TOKEN", "test-not-real")
    called = []

    def fetch(url, headers):
        called.append(url)
        page = (
            int(url.split("page%5Bnumber%5D=")[1].split("&")[0])
            if "page%5Bnumber%5D=" in url
            else int(url.split("page[number]=")[1].split("&")[0])
        )
        if page == 1:
            return (
                200,
                {},
                json.dumps(
                    {"data": DISCOS_SAMPLE["data"], "links": {"next": "yes"}}
                ).encode(),
            )
        return 200, {}, json.dumps({"data": [], "links": {"next": None}}).encode()

    archive.sync_discos_pages(max_pages=1, page_size=2, fetch=fetch)
    assert archive.state()[0]["cursor"] == "2"
    archive.sync_discos_pages(max_pages=1, page_size=2, fetch=fetch)
    assert archive.state()[0]["complete"] == 1
    assert len(called) == 2


def test_keeptrack_only_one_bulk_and_etag(archive, monkeypatch):
    monkeypatch.setenv("ORBITOBY_KEEPTRACK_API_KEY", "demo-not-real")
    calls = []

    def fetch(url, headers):
        calls.append((url, dict(headers)))
        return 200, {"ETag": '"v1"'}, json.dumps(KT_SAMPLE).encode()

    archive.sync_keeptrack(fetch=fetch)
    archive.sync_keeptrack(fetch=fetch)
    assert len(calls) == 1 and calls[0][0] == KEEPTRACK_BULK

    def not_modified(url, headers):
        assert headers["If-None-Match"] == '"v1"'
        return 304, {}, b""

    archive.sync_keeptrack(refresh=True, fetch=not_modified)


def test_no_token_refused(archive, monkeypatch):
    monkeypatch.delenv("ORBITOBY_DISCOS_TOKEN", raising=False)
    with pytest.raises(ArchiveError):
        archive.sync_discos_pages(max_pages=1)
    monkeypatch.delenv("ORBITOBY_KEEPTRACK_API_KEY", raising=False)
    with pytest.raises(ArchiveError):
        archive.sync_keeptrack()


def test_export_and_raw_receipts(archive, tmp_path):
    archive.import_gcat_tsv("satcat.tsv", GCAT_SAMPLE)
    out = archive.export_csv(tmp_path / "out.csv", required=("launch_mass_kg",))
    assert out.exists() and "35694" in out.read_text()
    snaps = list((tmp_path / "snapshots/gcat").glob("*.gz"))
    assert snaps and snaps[0].stat().st_size > 0


def test_bad_bulk_fails_closed(archive):
    with pytest.raises(ArchiveError):
        archive.import_keeptrack_bulk([{"name": "bad"}])
    assert archive.sources() == {}  # rollback, no partial ingest


def test_universe_audit_and_raw_field_lookup(archive):
    archive.import_gcat_tsv("satcat.tsv", GCAT_SAMPLE)
    archive.import_discos_page(
        DISCOS_SAMPLE, group="test", url="https://discosweb.esoc.esa.int/api/objects"
    )
    archive.import_keeptrack_bulk(KT_SAMPLE)
    result = archive.audit_universe([35694, 35693, 25544])
    assert result["reference_norad_count"] == 3
    assert all(
        x["matched"] == 2 and x["missing_norad_ids"] == [25544]
        for x in result["providers"].values()
    )
    assert (
        archive.find_raw("discos", "attributes.mass", expected=47.45)[0]["norad_id"]
        == 35694
    )
    assert (
        archive.find_raw("keeptrack", "BSTAR")[0]["value"] == 0.2
    )  # searchable, NOT converted to Cd


def test_wide_preserves_missing_ids_and_sources(archive, tmp_path):
    archive.import_gcat_tsv("satcat.tsv", GCAT_SAMPLE)
    archive.import_discos_page(
        DISCOS_SAMPLE, group="test", url="https://discosweb.esoc.esa.int/api/objects"
    )
    out = archive.export_wide(tmp_path / "wide.csv", universe=[35693, 35694, 25544])
    text = out.read_text()
    assert text.count("\n") == 4
    assert "gcat.launch_mass_kg" in text and "discos.cross_section_geo_avg_m2" in text
    assert "25544" in text


def test_keeptrack_official_brief_style_tle_identity(archive):
    tle1 = "1 25544U 98067A   21075.51041667  .00001264  00000-0  29616-4 0  9993"
    tle2 = "2 25544  51.6446  90.1228 0002261  70.5719  19.3391 15.48944243273144"
    n, m = archive.import_keeptrack_bulk(
        [
            {
                "id": 123,
                "name": "ISS",
                "type": 1,
                "tle1": tle1,
                "tle2": tle2,
                "purpose": "Science",
            }
        ]
    )
    assert n == m == 1
    assert archive.get(25544, provider="keeptrack")["records"][0]["raw"]["id"] == 123
    assert len(archive.get(123, provider="keeptrack")["records"]) == 0
