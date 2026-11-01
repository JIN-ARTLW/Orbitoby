"""No network: synthetic plot universe and GCAT rows, preserving missing IDs."""

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "orbitoby_join_all_physical_specs.py"
)
spec = importlib.util.spec_from_file_location("orbitoby_full_physical_join", SCRIPT)
impl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(impl)


def test_plot_universe_unique_and_audit(tmp_path):
    folder = tmp_path / "plot"
    folder.mkdir()
    (folder / "satellite_monthly_le550.csv").write_text(
        "norad_id,epoch,is_cubesat,alt_km\n10,2009-01-01,true,520\n10,2009-02-01,true,519\n20,2010-01-01,false,470\n",
        encoding="utf-8",
    )
    (folder / "first_tle_altitude_eligibility_audit.csv").write_text(
        "norad_id,first_alt_km,starts_within_altitude_band\n10,520,true\n20,470,true\n30,630,false\n",
        encoding="utf-8",
    )
    universe, _ = impl.read_universe(folder)
    assert len(universe) == 2
    assert universe["plotted_records"].tolist() == [2, 1]
    merged, _ = impl.read_first_tle_audit(folder, universe)
    assert merged["first_alt_km"].tolist() == [520, 470]
    assert len(merged) == 2  # rejected object 30 not included


def test_all_norad_ids_remain_with_missing_specs():
    base = pd.DataFrame({"norad_id": [10, 20, 30], "plotted_records": [4, 5, 1]})
    gcat = pd.DataFrame(
        {
            "norad_id": [10],
            "launch_mass_kg": [2.5],
            "mass_known": [True],
            "mass_unflagged": [True],
            "dimensions_known": [True],
            "panel_documented": [False],
            "surface_area_documented": [False],
            "drag_area_documented": [False],
            "strict_documented": [False],
            "completeness_tier": ["catalog_physical_partial"],
            "solar_panel_status": ["unknown"],
            "object_type": ["P"],
        }
    )
    joined = impl.full_left_join(base, gcat, {30})
    assert len(joined) == 3
    assert joined["norad_id"].tolist() == [10, 20, 30]
    assert joined["gcat_match_status"].tolist() == [
        "matched",
        "no_gcat_match",
        "ambiguous_gcat_norad",
    ]
    metrics = impl.summarize(joined, base, expected_count=3)
    assert metrics["gcat_matched"] == 1
    assert metrics["gcat_unmatched"] == 1
    assert metrics["gcat_ambiguous"] == 1
    assert metrics["catalog_partial_candidates"] == 1
    with pytest.raises(ValueError, match="Expected exactly"):
        impl.summarize(joined, base, expected_count=4)


def test_reject_silent_invalid_id(tmp_path):
    folder = tmp_path
    (folder / "satellite_monthly_le550.csv").write_text(
        "norad_id,epoch\n10,2009-01-01\nbroken,2009-02-01\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="Unparseable"):
        impl.read_universe(folder)


def test_no_duplicate_spec_join():
    base = pd.DataFrame({"norad_id": [10, 20]})
    gcat = pd.DataFrame({"norad_id": [10, 10], "launch_mass_kg": [1.0, 2.0]})
    with pytest.raises(ValueError, match="duplicate NORAD"):
        impl.full_left_join(base, gcat, set())
