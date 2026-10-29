"""Science Day feature contract tests are offline and deterministic."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pandas as pd
import pytest

from orbitoby import _science_day as sd


def _evidence(name):
    return {
        "feed": name,
        "provider": "CelesTrak",
        "provider_url": "https://celestrak.org/pub/satcat.csv",
        "sha256": "verified-digest-for-test",
    }


def test_catalog_merges_memberships_without_double_count(monkeypatch):
    feeds = {
        "satcat": [
            {"NORAD_CAT_ID": "100001", "SATNAME": "STARLINK-NEW"},
            {"NORAD_CAT_ID": "22", "SATNAME": "TEST"},
        ],
        "active_gp": [
            {
                "NORAD_CAT_ID": 100001,
                "OBJECT_NAME": "STARLINK-NEW",
                "EPOCH": "2026-10-28T00:00:00Z",
            }
        ],
        "starlink_gp": [{"NORAD_CAT_ID": 100001, "OBJECT_NAME": "STARLINK-NEW"}],
        "spacex_supgp": [
            {"NORAD_CAT_ID": 100001, "OBJECT_NAME": "STARLINK-NEW"},
            {"NORAD_CAT_ID": 100002, "OBJECT_NAME": "STARLINK-UNLISTED"},
        ],
    }
    monkeypatch.setattr(
        sd, "_sat_raw", lambda name, refresh: (feeds[name], _evidence(name))
    )
    result = sd.catalog("all")
    assert set(result.table.norad_id) == {22, 100001, 100002}
    assert len(result.table) == 3
    assert len(result.sources().table) == 4
    assert set(sd.catalog("starlink").table.norad_id) == {100001, 100002}
    assert set(sd.catalog("active").table.norad_id) == {100001}
    assert set(result.pick(22).table.norad_id) == {22}
    with pytest.raises(ValueError, match="not in"):
        result.pick(999999)


def test_f107_parsing_misses_zero_records_and_keeps_measured_utc():
    source = {
        "provider_url": "https://spaceweather.gc.ca/solar_flux_data/daily_flux_values/fluxtable.txt"
    }
    historic = (
        b"2432187.20,1248.27,1947,01,01,.0,.0,.0\n"
        b"2432188.20,1248.31,1947,01,02,71.2,72.3,65.4\n"
    )
    parsed = sd._parse_nr_legacy(historic, source)
    assert len(parsed) == 2
    assert {p["metric"] for p in parsed} == {"F10.7 observed", "F10.7 adjusted"}
    assert all(p["timestamp"] == datetime(1947, 1, 2, tzinfo=UTC) for p in parsed)
    modern = (
        b"fluxdate fluxtime fluxjulian fluxcarrington fluxobsflux fluxadjflux fluxursi\n"
        b"20041028 170000 02453307.229 002022.605 000132.7 000130.9 000117.8\n"
    )
    rows = sd._parse_nr_modern(modern, source)
    assert len(rows) == 2
    assert rows[0]["timestamp"] == datetime(2004, 10, 28, 17, 0, tzinfo=UTC)
    assert rows[0]["value"] == pytest.approx(132.7)


def test_silso_provisional_marker_and_missing():
    source = {"provider_url": "https://www.sidc.be/SILSO/DATA/SN_ms_tot_V2.0.csv"}
    raw = "2024;10;2024.79;150.5;2.5;100;1\n2024;11;2024.87;-1;0;0;0\n"
    rows = sd._parse_silso(raw.encode(), source)
    assert len(rows) == 1
    assert rows[0]["value"] == 150.5
    assert rows[0]["status"] == "1"


def test_where_half_open_and_immutable(tmp_path):
    table = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2024-01-01", "2024-01-02", "2024-01-03"], utc=True
            ),
            "value": [90, 201, 250],
        }
    )
    result = sd.ResearchResult(
        table,
        name="F10.7",
        role="measurement",
        unit="sfu",
        sources=[_evidence("solar")],
    )
    subset = result.where(above=200, start="2024-01-02", end="2024-01-03")
    assert subset.table.value.tolist() == [201]
    assert result.table.value.tolist() == [90, 201, 250]
    file = subset.save(tmp_path / "research.csv")
    metadata = json.loads(file.with_suffix(".csv.sources.json").read_text())
    assert metadata["operations"][-1]["above_inclusive"] == 200
    assert metadata["rows"] == 1
    assert file.exists()


def test_offline_plot_png_and_svg(tmp_path):
    pytest.importorskip("matplotlib")
    result = sd.ResearchResult(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2024-01-01", "2024-01-02"], utc=True),
                "value": [120.5, 220.5],
            }
        ),
        name="F10.7",
        role="measurement",
        unit="sfu",
        sources=[_evidence("solar")],
    )
    fig = result.plot(highlight=("2024-01-01", "2024-01-03"), above=200)
    for ext in ("svg", "png"):
        target = fig.save(tmp_path / f"figure.{ext}")
        assert target.exists()
        meta = target.with_suffix(f".{ext}.sources.json")
        assert meta.exists()
        assert json.loads(meta.read_text())["plot"]["above_inclusive"] == 200
    assert "CelesTrak" in fig.sources().table.provider.to_list()


def test_sources_sanitized():
    with pytest.raises(ValueError):
        sd._clean_url("http://celestrak.org/pub/satcat.csv")
    with pytest.raises(ValueError):
        sd._clean_url("https://evil.example/?token=123")


def test_f107_same_day_product_policy_and_sources(monkeypatch):
    """Never combine daily placeholders and real 3/day measurements."""

    def offline_obtain(path, url, **kwargs):
        if "F107_1947_1996" in url:
            raw = b"2432188.20,1248.31,2004,10,28,71.2,72.3,65.4\n"
        elif "F107_1996_2007" in url:
            raw = b"2453307.2 2022.6 2004 10 28 1700 91.2 92.3 89.0\n"
        elif "fluxtable.txt" in url:
            raw = (
                b"20041028 170000 02453307.229 002022.605 000132.7 000130.9 000117.8\n"
                b"20041028 200000 02453307.354 002022.610 000140.0 000138.0 000120.0\n"
            )
        else:
            raise AssertionError(f"Unexpected endpoint {url}")
        return raw, {
            "provider_url": url,
            "feed": "test",
            "sha256": "test",
            "provider": "NRCan",
        }

    monkeypatch.setattr(sd, "_obtain", offline_obtain)
    result = sd.solar_history("F10.7", "2004-10-28", "2004-10-29")
    assert len(result.table) == 2
    assert result.table["value"].tolist() == pytest.approx([132.7, 140.0])
    assert set(result.table["product"]) == {"modern_three_daily_readings"}
    assert len(result.sources().table) == 1
    assert result.sources().table.iloc[0]["provider_url"].endswith("fluxtable.txt")
