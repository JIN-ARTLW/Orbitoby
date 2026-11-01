from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "orbitoby_full_catalog_physics",
    ROOT / "scripts" / "orbitoby_full_catalog_physics.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def gcat_sample():
    return pd.DataFrame(
        [
            {
                "norad_id": 1,
                "object_name": "A",
                "object_type": "P",
                "launch_mass_kg": 10.0,
                "launch_mass_flag": "",
                "body_length_m": 1.0,
                "body_diameter_m": 0.5,
                "discos_mass_kg": float("nan"),
            },
            {
                "norad_id": 2,
                "object_name": "Rocket body",
                "object_type": "R",
                "launch_mass_kg": 50.0,
                "launch_mass_flag": "?",
                "body_length_m": 2.0,
                "body_diameter_m": 1.0,
                "discos_mass_kg": float("nan"),
            },
        ]
    )


def universe_sample():
    return pd.DataFrame(
        {
            "norad_id": [1, 2, 3],
            "orbitoby_object_type": ["PAYLOAD", "ROCKET BODY", "PAYLOAD"],
            "orbitoby_object_name": ["A", "R", "C"],
        }
    )


def test_full_universe_no_orbit_filter():
    out = mod.build_table(
        universe_sample(),
        gcat_sample(),
        pd.DataFrame(columns=["norad_id"]),
        pd.DataFrame(columns=mod.DISCOS_COLS),
        pd.DataFrame(columns=mod.MANUAL_COLS),
    )
    assert len(out) == 3
    assert list(out.norad_id) == [1, 2, 3]
    assert out.set_index("norad_id").loc[3, "gcat_match_status"] == "not_found"
    assert out.set_index("norad_id").loc[3, "object_class"] == "payload"
    assert not out["ballistic_coefficient_available"].any()
    assert not out["has_documented_drag_area"].any()


def test_discos_catalog_area_is_not_drag_area():
    disc = pd.DataFrame(
        [{"norad_id": 1, "discos_mass_kg": 12.0, "discos_xsect_avg_m2": 0.5}]
    )
    out = mod.build_table(
        universe_sample(),
        gcat_sample(),
        pd.DataFrame(columns=["norad_id"]),
        disc,
        pd.DataFrame(columns=mod.MANUAL_COLS),
    )
    row = out.set_index("norad_id").loc[1]
    assert row["has_discos_catalog_area"]
    assert row["catalog_m_a_geometry_proxy_kg_m2"] == 24
    assert not row["ballistic_coefficient_available"]


def test_manual_documented_coefficient():
    man = pd.DataFrame(
        [
            {
                "norad_id": 1,
                "configuration_context_id": "mission-2010-A",
                "mass_kg": 10.0,
                "mass_source_url": "https://example.org/mass",
                "drag_projected_area_m2": 2.0,
                "drag_area_source_url": "https://example.org/area",
                "drag_coefficient": 2.5,
                "cd_source_url": "https://example.org/cd",
                "attitude_context": "fixed known orientation",
            }
        ]
    )
    out = mod.build_table(
        universe_sample(),
        gcat_sample(),
        pd.DataFrame(columns=["norad_id"]),
        pd.DataFrame(columns=mod.DISCOS_COLS),
        man,
    )
    row = out.set_index("norad_id").loc[1]
    assert row["ballistic_coefficient_computed_kg_m2"] == 2.0
    assert row["inverse_ballistic_coefficient_computed_m2_kg"] == 0.5
    assert row["physical_evidence_tier"] == "A_documented_or_calculable_B"


def test_mass_without_documented_area_does_not_calculate_bc():
    man = pd.DataFrame(
        [
            {
                "norad_id": 1,
                "configuration_context_id": "A",
                "mass_kg": 10.0,
                "mass_source_url": "https://example.org/m",
                "drag_coefficient": 2.5,
                "cd_source_url": "https://example.org/c",
                "attitude_context": "fixed",
            }
        ]
    )
    out = mod.build_table(
        universe_sample(),
        gcat_sample(),
        pd.DataFrame(columns=["norad_id"]),
        pd.DataFrame(columns=mod.DISCOS_COLS),
        man,
    )
    assert not out.set_index("norad_id").loc[1, "ballistic_coefficient_available"]


def test_manual_requires_source(tmp_path):
    p = tmp_path / "evidence.csv"
    pd.DataFrame([{"norad_id": 1, "mass_kg": 10.0}]).to_csv(p, index=False)
    with pytest.raises(ValueError, match="source URL"):
        mod.import_manual_csv(p)


def test_explicit_catalog_csv(tmp_path):
    p = tmp_path / "all_catalog.csv"
    pd.DataFrame(
        {"NORAD_CAT_ID": [1, 2, 3], "OBJECT_TYPE": ["PAYLOAD", "DEBRIS", "PAYLOAD"]}
    ).to_csv(p, index=False)
    rows, src = mod.load_universe(catalog_csv=p)
    assert rows.norad_id.tolist() == [1, 2, 3]
    assert "sha256" in src


def test_export_keeps_unmatched(tmp_path):
    out = mod.build_table(
        universe_sample(),
        gcat_sample(),
        pd.DataFrame(columns=["norad_id"]),
        pd.DataFrame(columns=mod.DISCOS_COLS),
        pd.DataFrame(columns=mod.MANUAL_COLS),
    )
    metrics = mod.write_outputs(
        out,
        {"source": "test"},
        [],
        None,
        None,
        pd.DataFrame(columns=["norad_id"]),
        tmp_path,
    )
    assert metrics["entire_orbitoby_catalog_objects"] == 3
    assert metrics["classified_payload_satellites"] == 2
    assert metrics["payloads_documented_ballistic_coefficient"] == 0
    assert len(pd.read_csv(tmp_path / "all_catalog_norad_physical_evidence.csv")) == 3
    assert len(pd.read_csv(tmp_path / "satellites_mass_and_dimensions.csv")) == 1


def test_sphere_body_area_not_drag_area():
    gc = gcat_sample().copy()
    gc["shape_description"] = ["Sphere", "Cylinder"]
    out = mod.build_table(
        universe_sample(),
        gc,
        pd.DataFrame(columns=["norad_id"]),
        pd.DataFrame(columns=mod.DISCOS_COLS),
        pd.DataFrame(columns=mod.MANUAL_COLS),
    )
    row = out.set_index("norad_id").loc[1]
    assert round(row["sphere_body_reference_cross_section_m2"], 7) == round(
        3.141592653589793 * 0.25**2, 7
    )
    assert not row["has_documented_drag_area"]
