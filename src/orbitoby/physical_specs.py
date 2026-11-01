"""Orbitoby optional physical-property evidence adapters (GCAT + ESA DISCOS).

Scientific guarantees:
- TLE mean elements do not provide mass, surface area or solar-array configuration.
- GCAT launch/dry mass and body dimensions are metadata, not proven in-orbit
  mass or attitude-dependent drag cross-section.
- DISCOS xSectAvg/Min/Max are catalog geometric cross-section descriptors,
  not physical drag coefficients or guaranteed in-orbit projected areas.
- A panel state cannot be inferred from `span` or shape strings.
- strict documented cohort requires explicit per-field evidence, and is only
  a *documentation-completeness gate*, not proof of physical correctness.

No top-level network activity or hard dependency beyond pandas.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

GCAT_CATALOGS = {
    "satcat": "https://planet4589.org/space/gcat/tsv/cat/satcat.tsv",
    "satcat100k": "https://planet4589.org/space/gcat/tsv/cat/satcat100k.tsv",
}
GCAT_DOC = "https://planet4589.org/space/gcat/web/cat/cols.html"
DISCOS_URL = "https://discosweb.esoc.esa.int/api/objects"
DISCOS_SOURCE = "https://discosweb.esoc.esa.int/"


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _download(url: str, *, token: str | None = None, timeout: float = 40, max_bytes: int = 45_000_000):
    headers = {"User-Agent": "OrbitobyResearchPhysicalSpecs/0.1 (+scientific provenance)"}
    if token:
        headers.update({"Authorization": f"Bearer {token}", "DiscosWeb-Api-Version": "2"})
    with urlopen(Request(url, headers=headers), timeout=timeout) as response:
        raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError(f"Source response exceeds {max_bytes} bytes")
    if not raw:
        raise ValueError(f"Source response is empty: {url}")
    return raw


def retrieve_gcat(cache_dir: str | Path, *, catalogs: tuple[str, ...] = ("satcat", "satcat100k"), refresh=False):
    """Return cached file paths and per-file SHA256 manifests; no redistribution of raw catalogs."""
    root = Path(cache_dir).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    receipts = []
    paths = []
    for catalog in catalogs:
        if catalog not in GCAT_CATALOGS:
            raise ValueError(f"Unknown GCAT catalog {catalog!r}")
        path = root / f"gcat_{catalog}.tsv"
        mode = "cache"
        if refresh or not path.is_file():
            raw = _download(GCAT_CATALOGS[catalog])
            temp = path.with_suffix(".tsv.partial")
            temp.write_bytes(raw)
            temp.replace(path)
            mode = "download"
        raw = path.read_bytes()
        paths.append(path)
        receipts.append({
            "provider": "Jonathan McDowell GCAT", "dataset": catalog,
            "source_url": GCAT_CATALOGS[catalog], "documentation_url": GCAT_DOC,
            "retrieved_or_cache": mode, "local_path": str(path),
            "sha256": sha256(raw), "bytes": len(raw),
            "checked_utc": datetime.now(timezone.utc).isoformat(),
        })
    return paths, receipts


def _read_gcat_tsv(raw: bytes):
    """GCAT TSV starts with a #JCAT tab-separated header; ignore later comment lines."""
    text = raw.decode("utf-8-sig", errors="replace")
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("#JCAT\t") or line.startswith("JCAT\t"):
            header = line[1:] if line.startswith("#") else line
            body = [header] + [part for part in lines[i + 1:] if part and not part.lstrip().startswith("#")]
            return pd.read_csv(io.StringIO("\n".join(body)), sep="\t", dtype=str, keep_default_na=False)
    raise ValueError("GCAT TSV header '#JCAT\\t...' not found; source format may have changed")


def _col(df, *names):
    lower = {str(c).casefold(): c for c in df.columns}
    for name in names:
        if name.casefold() in lower:
            return lower[name.casefold()]
    return None


def _number(v):
    val = str(v).strip().replace(',', '')
    if not val or val in ("-", "?", "--"):
        return math.nan
    try:
        n = float(val)
        return n if math.isfinite(n) and n > 0 else math.nan
    except (ValueError, TypeError):
        return math.nan


def _flag(v):
    return str(v).strip()


def parse_gcat(raw: bytes, *, catalog_name: str = "satcat") -> pd.DataFrame:
    """Parse physical metadata and source qualifiers; malformed/ambiguous IDs are skipped."""
    source = _read_gcat_tsv(raw)
    fields = {
        "satcat": _col(source, "Satcat"),
        "name": _col(source, "Name", "Satname"),
        "type": _col(source, "Type"),
        "mass": _col(source, "Mass"), "mass_flag": _col(source, "MassFlag"),
        "dry_mass": _col(source, "DryMass"), "dry_mass_flag": _col(source, "DryFlag"),
        "length": _col(source, "Length"), "length_flag": _col(source, "LFlag"),
        "diameter": _col(source, "Diameter"), "diameter_flag": _col(source, "DFlag"),
        "span": _col(source, "Span"), "span_flag": _col(source, "SpanFlag"),
        "shape": _col(source, "Shape"),
    }
    for mandatory in ("satcat", "mass", "length", "shape"):
        if fields[mandatory] is None:
            raise ValueError(f"Required GCAT field {mandatory} missing; found {list(source.columns)}")
    records = []
    for _, row in source.iterrows():
        val = str(row[fields["satcat"]]).strip()
        if not re.fullmatch(r"\d{1,9}", val):
            continue
        def get(field):
            col = fields[field]
            return str(row[col]).strip() if col else ""
        norad = int(val)
        records.append({
            "norad_id": norad,
            "object_name": get("name"), "object_type": get("type"),
            "launch_mass_kg": _number(get("mass")),
            "launch_mass_flag": _flag(get("mass_flag")),
            "dry_mass_kg": _number(get("dry_mass")),
            "dry_mass_flag": _flag(get("dry_mass_flag")),
            "body_length_m": _number(get("length")),
            "body_length_flag": _flag(get("length_flag")),
            "body_diameter_m": _number(get("diameter")),
            "body_diameter_flag": _flag(get("diameter_flag")),
            "total_span_m": _number(get("span")),
            "total_span_flag": _flag(get("span_flag")),
            "shape_description": get("shape"),
            "catalog_name": catalog_name, "gcat_source_url": GCAT_CATALOGS.get(catalog_name, ""),
            "solar_panel_status": "unknown", "solar_panel_source_url": "",
            "surface_area_m2": math.nan, "surface_area_source_url": "",
            "drag_projected_area_m2": math.nan, "drag_area_source_url": "",
            "attitude_context": "unknown", "discos_xsect_avg_m2": math.nan,
            "discos_xsect_min_m2": math.nan, "discos_xsect_max_m2": math.nan,
            "discos_mass_kg": math.nan,
        })
    result = pd.DataFrame(records)
    if result.empty:
        return result
    result = result.sort_values("norad_id").drop_duplicates("norad_id", keep="last").reset_index(drop=True)
    return result


def load_gcat(paths: list[str | Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        name = Path(path).stem.removeprefix("gcat_")
        frames.append(parse_gcat(Path(path).read_bytes(), catalog_name=name))
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        raise ValueError("No GCAT entries with numeric NORAD IDs")
    merged = pd.concat(frames, ignore_index=True)
    if merged.norad_id.duplicated().any():
        raise ValueError("Conflicting NORAD IDs across source catalogs; inspect rather than overwrite")
    return merged


def parse_discos_response(data: dict, requested_norad: int) -> dict | None:
    """Parse the v2 JSON API; never confuse xSectAvg with measured in-orbit A_drag."""
    raw_items = data.get("data", [])
    items = raw_items if isinstance(raw_items, list) else [raw_items]
    for item in items:
        attrs = item.get("attributes", {})
        if str(attrs.get("satno", "")).strip() != str(requested_norad):
            continue
        return {
            "norad_id": requested_norad,
            "discos_mass_kg": _number(attrs.get("mass", "")),
            "discos_shape": str(attrs.get("shape", "")),
            "discos_xsect_avg_m2": _number(attrs.get("xSectAvg", "")),
            "discos_xsect_min_m2": _number(attrs.get("xSectMin", "")),
            "discos_xsect_max_m2": _number(attrs.get("xSectMax", "")),
            "discos_source_url": DISCOS_SOURCE,
        }
    return None


def query_discos(norad_ids: list[int], *, token: str | None = None) -> tuple[pd.DataFrame, list]:
    """Opt-in authenticated queries. No tokens saved or echoed. Max 30 IDs per call."""
    token = token or os.environ.get("ORBITOBY_DISCOS_TOKEN", "")
    if not token:
        raise ValueError("DISCOS token missing; set ORBITOBY_DISCOS_TOKEN locally")
    if len(norad_ids) > 30:
        raise ValueError("Query at most 30 NORAD IDs per run to limit API load")
    records, receipts = [], []
    for norad_id in norad_ids:
        url = DISCOS_URL + "?" + urlencode({"filter": f"eq(satno,{int(norad_id)})"})
        try:
            raw = _download(url, token=token, max_bytes=1_000_000)
            data = json.loads(raw.decode("utf-8"))
            parsed = parse_discos_response(data, int(norad_id))
            receipts.append({"norad_id": int(norad_id), "url": url, "found": parsed is not None,
                             "api_version": "2", "response_sha256": sha256(raw),
                             "checked_utc": datetime.now(timezone.utc).isoformat()})
            if parsed:
                records.append(parsed)
        except Exception as exc:
            receipts.append({"norad_id": int(norad_id), "url": url,
                             "error": f"{type(exc).__name__}: {exc}"})
    return pd.DataFrame(records), receipts


def attach_discos(gcat: pd.DataFrame, discos: pd.DataFrame) -> pd.DataFrame:
    if discos.empty:
        return gcat.copy()
    if discos.norad_id.duplicated().any():
        raise ValueError("Duplicate DISCOS NORAD identifiers")
    # Preserve GCAT columns with the same names, overwrite with independently
    # sourced values only where DISCOS provides a non-missing value.
    out = gcat.copy().set_index("norad_id")
    for _, r in discos.iterrows():
        id_value = int(r["norad_id"])
        if id_value not in out.index:
            continue
        for k in ("discos_mass_kg", "discos_shape", "discos_xsect_avg_m2", "discos_xsect_min_m2", "discos_xsect_max_m2", "discos_source_url"):
            if k in r.index and pd.notna(r[k]) and str(r[k]).strip():
                out.loc[id_value, k] = r[k]
    return out.reset_index()


PANEL_STATES = {"present", "absent", "unknown"}
REQUIRED_MANUAL = ("norad_id", "solar_panel_status", "solar_panel_source_url",
                   "surface_area_m2", "surface_area_source_url",
                   "drag_projected_area_m2", "drag_area_source_url", "attitude_context")


def attach_documented_evidence(gcat: pd.DataFrame, evidence: pd.DataFrame):
    """Attach manually audited mission-doc evidence. All records need NORAD ID; no name matching."""
    missing = set(REQUIRED_MANUAL) - set(evidence.columns)
    if missing:
        raise ValueError(f"Evidence CSV missing columns: {sorted(missing)}")
    ev = evidence.copy()
    ev["norad_id"] = pd.to_numeric(ev["norad_id"], errors="raise").astype("int64")
    if ev.norad_id.duplicated().any():
        raise ValueError("Evidence contains duplicate NORAD IDs")
    out = gcat.copy().set_index("norad_id")
    for _, row in ev.iterrows():
        identifier = int(row.norad_id)
        if identifier not in out.index:
            continue
        status = str(row.solar_panel_status).strip().lower()
        if status not in PANEL_STATES:
            raise ValueError(f"Invalid solar_panel_status for NORAD {identifier}: {status}")
        out.loc[identifier, "solar_panel_status"] = status
        for key in REQUIRED_MANUAL[2:]:
            if key in ("surface_area_m2", "drag_projected_area_m2"):
                out.loc[identifier, key] = _number(row[key])
            else:
                out.loc[identifier, key] = str(row[key]).strip() if pd.notna(row[key]) else ""
    return out.reset_index()


def rank_completeness(df: pd.DataFrame) -> pd.DataFrame:
    """Documentation coverage, not measured accuracy. Missing values remain missing."""
    out = df.copy()
    for col in ("launch_mass_kg", "body_length_m", "body_diameter_m", "surface_area_m2", "drag_projected_area_m2"):
        if col not in out:
            out[col] = math.nan
    for col in ("surface_area_source_url", "drag_area_source_url", "solar_panel_source_url", "solar_panel_status", "attitude_context"):
        if col not in out:
            out[col] = ""
    out["mass_known"] = pd.to_numeric(out.launch_mass_kg, errors="coerce").gt(0)
    out["mass_unflagged"] = out.mass_known & ~out.get("launch_mass_flag", pd.Series("?", index=out.index)).astype(str).str.contains("\\?", regex=True)
    out["dimensions_known"] = pd.to_numeric(out.body_length_m, errors="coerce").gt(0) & pd.to_numeric(out.body_diameter_m, errors="coerce").gt(0)
    out["panel_documented"] = out.solar_panel_status.isin(("present", "absent")) & out.solar_panel_source_url.astype(str).str.startswith(('https://', 'http://'))
    out["surface_area_documented"] = pd.to_numeric(out.surface_area_m2, errors="coerce").gt(0) & out.surface_area_source_url.astype(str).str.startswith(('https://','http://'))
    out["drag_area_documented"] = pd.to_numeric(out.drag_projected_area_m2, errors="coerce").gt(0) & out.drag_area_source_url.astype(str).str.startswith(('https://','http://'))
    out["strict_documented"] = (out.mass_unflagged & out.dimensions_known & out.panel_documented &
                                out.surface_area_documented & out.drag_area_documented &
                                ~out.attitude_context.astype(str).str.lower().isin(("", "unknown")))
    out["completeness_tier"] = "incomplete"
    out.loc[out.mass_known & out.dimensions_known, "completeness_tier"] = "catalog_physical_partial"
    out.loc[out.strict_documented, "completeness_tier"] = "strict_documented"
    return out


def cohort(df: pd.DataFrame, *, min_tier: str = "catalog_physical_partial", payload_only: bool = True) -> pd.DataFrame:
    """Select catalog completeness or explicitly documented research-usable cohort.

    By default, exclude rocket bodies, fragments and components. GCAT Type
    begins with 'P' for payloads; this is a catalog class, not a maneuver audit.
    """
    if min_tier not in ("all", "catalog_physical_partial", "strict_documented"):
        raise ValueError(f"Unknown filter tier: {min_tier}")
    out = df.copy()
    if payload_only:
        if 'object_type' not in out.columns:
            raise ValueError('Missing GCAT object_type; cannot safely select payload-only')
        out = out.loc[out.object_type.fillna('').astype(str).str.startswith('P')].copy()
    if min_tier == "all":
        return out
    if min_tier == "strict_documented":
        return out.loc[out.strict_documented].copy()
    return out.loc[out.mass_known & out.dimensions_known].copy()


def join_orbit_csv(specs: pd.DataFrame, orbit_csv: str | Path, *, strict=False) -> pd.DataFrame:
    """Join to pre-generated Orbitoby orbit summary/records on NORAD ID only."""
    orbit = pd.read_csv(orbit_csv)
    id_col = _col(orbit, "norad_id", "NORAD_CAT_ID", "satnum")
    if id_col is None:
        raise ValueError("Orbit CSV must contain NORAD ID column")
    orbit = orbit.rename(columns={id_col: "norad_id"})
    orbit["norad_id"] = pd.to_numeric(orbit["norad_id"], errors="coerce").astype("Int64")
    use = cohort(specs, min_tier="strict_documented" if strict else "catalog_physical_partial")
    return orbit.merge(use, on="norad_id", how="inner", validate="many_to_one", suffixes=("", "_physical"))
