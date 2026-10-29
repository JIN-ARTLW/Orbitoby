"""Offline regression for the Science Day progressive API and source-rich exports."""

import hashlib
import json

import pandas as pd
import pytest

import orbitoby as ob
from orbitoby import _science_day as sd


def source(feed, url="https://celestrak.org/pub/satcat.csv"):
    return {
        "feed": feed,
        "provider": "CelesTrak",
        "provider_url": url,
        "sha256": "example-fixture-hash",
    }


def test_study_science_day_facade(monkeypatch):
    calls = []

    def fake_catalog(group, *, refresh):
        calls.append(("catalog", group, refresh))
        return "catalog-result"

    def fake_solar(metric, start, end, *, refresh):
        calls.append(("solar", metric, str(start), str(end), refresh))
        return "solar-result"

    monkeypatch.setattr(sd, "catalog", fake_catalog)
    monkeypatch.setattr(sd, "solar_history", fake_solar)
    study = ob.study("2024-01-01", "2024-02-01")
    try:
        assert study.catalog("starlink") == "catalog-result"
        assert study.solar("F10.7") == "solar-result"
        assert calls[0] == ("catalog", "starlink", False)
        assert calls[1][0:2] == ("solar", "F10.7")
        assert calls[1][2:4] == ("2024-01-01", "2024-02-01")
    finally:
        study.close()


def test_catalog_find_pick_ids_and_exact_contributing_feeds():
    table = pd.DataFrame(
        {
            "norad_id": [22, 39452, 100001],
            "name": ["VANGUARD", "SWARM A", "STARLINK-TEST"],
            "satcat": [True, True, True],
            "active_gp": [False, True, True],
            "starlink_gp": [False, False, True],
            "spacex_supgp": [False, False, True],
        }
    )
    sources = [
        source(feed) for feed in ("satcat", "active_gp", "starlink_gp", "spacex_supgp")
    ]
    result = sd.ResearchResult(
        table,
        name="catalog",
        role="catalogue_membership_not_orbital_history",
        sources=sources,
    )
    selected = result.find("swarm").pick(39452)
    assert selected.ids == (39452,)
    assert set(selected.sources().table.feed) == {"satcat", "active_gp"}
    assert result.find("100001").ids == (100001,)
    assert result.ids == (22, 39452, 100001)
    assert set(result.sources().table.feed) == {source["feed"] for source in sources}
    with pytest.raises(ValueError, match="No satellite"):
        result.find("not-a-satellite")
    assert len(result.table) == 3  # immutable selection


def test_where_source_tracking_after_temporal_filter():
    url_a = "https://spaceweather.gc.ca/solar_flux_data/daily_flux_values/F107_1947_1996.txt"
    url_b = "https://spaceweather.gc.ca/solar_flux_data/daily_flux_values/fluxtable.txt"
    table = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["1955-01-01", "2024-01-01"], utc=True),
            "value": [73.0, 200.0],
            "provider_url": [url_a, url_b],
        }
    )
    result = sd.ResearchResult(
        table,
        name="F10.7",
        role="measurement",
        unit="sfu",
        sources=[source("historic", url_a), source("modern", url_b)],
    )
    chosen = result.where(start="2024-01-01", end="2025-01-01")
    assert len(chosen.table) == 1
    assert chosen.sources().table.feed.tolist() == ["modern"]
    assert len(result.sources().table) == 2


def test_science_day_bundle_csv_svg_png_manifest(tmp_path):
    pytest.importorskip("matplotlib")
    url = "https://spaceweather.gc.ca/solar_flux_data/daily_flux_values/fluxtable.txt"
    data = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2024-01-01", "2024-01-02", "2024-01-03"], utc=True
            ),
            "value": [111.0, 233.0, 155.0],
            "provider_url": [url] * 3,
        }
    )
    result = sd.ResearchResult(
        data,
        name="F10.7",
        role="measurement",
        unit="sfu",
        sources=[source("NRCan modern", url)],
    )
    destination = result.export(
        tmp_path / "solar_bundle", highlight=("2024-01-01", "2024-01-03"), above=200
    )
    filenames = {f.name for f in destination.iterdir()}
    assert {
        "data.csv",
        "data.csv.sources.json",
        "figure.svg",
        "figure.png",
        "figure.svg.sources.json",
        "figure.png.sources.json",
        "bundle_manifest.json",
    } <= filenames
    manifest = json.loads(
        (destination / "bundle_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["input_rows"] == 3
    assert manifest["sources"][0]["feed"] == "NRCan modern"
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((destination / name).read_bytes()).hexdigest() == digest
    with pytest.raises(FileExistsError):
        result.export(destination)


def test_catalog_export_without_figure(tmp_path):
    frame = pd.DataFrame(
        {"norad_id": [100001], "name": ["STARLINK-X"], "satcat": [True]}
    )
    result = sd.ResearchResult(
        frame,
        name="starlink",
        role="catalogue_membership_not_orbital_history",
        sources=[source("satcat")],
    )
    folder = result.export(tmp_path / "cat")
    assert (folder / "data.csv").is_file()
    assert not (folder / "figure.png").exists()
    assert result.ids == (100001,)
