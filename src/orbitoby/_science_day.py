"""Science Day research layer: satellite catalogues, solar history and traceable exports.

Designed to add read-only research capabilities without changing Archive semantics.
Network use is explicit where possible; raw downloads are cached with SHA-256.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

import pandas as pd

_CACHE = Path.home() / "Library/Caches/orbitoby"
_RAW_SOLAR = _CACHE / "science_day_solar"
_RAW_SAT = _CACHE / "v020_satellites"
_EVIDENCE = Path.home() / "Documents/OrbitobyResearch/v020_evidence/raw"
_ALLOWED_HOSTS = {
    "celestrak.org",
    "www.celestrak.org",
    "spaceweather.gc.ca",
    "www.spaceweather.gc.ca",
    "sidc.be",
    "www.sidc.be",
    "kp.gfz.de",
}
_SAT = {
    "satcat": ("csv", "https://celestrak.org/pub/satcat.csv", timedelta(hours=12)),
    "active_gp": (
        "json",
        "https://celestrak.org/NORAD/elements/gp.php?GROUP=ACTIVE&FORMAT=JSON",
        timedelta(hours=2),
    ),
    "starlink_gp": (
        "json",
        "https://celestrak.org/NORAD/elements/gp.php?GROUP=STARLINK&FORMAT=JSON",
        timedelta(hours=2),
    ),
    "spacex_supgp": (
        "json",
        "https://celestrak.org/NORAD/elements/supplemental/sup-gp.php?SOURCE=SpaceX-E&FORMAT=JSON",
        timedelta(hours=2),
    ),
}
_F107 = {
    "historic": "https://spaceweather.gc.ca/solar_flux_data/daily_flux_values/F107_1947_1996.txt",
    "bridge": "https://spaceweather.gc.ca/solar_flux_data/daily_flux_values/F107_1996_2007.txt",
    "modern": "https://spaceweather.gc.ca/solar_flux_data/daily_flux_values/fluxtable.txt",
}
_SILSO = "https://www.sidc.be/SILSO/DATA/SN_ms_tot_V2.0.csv"
_GFZ = "https://kp.gfz.de/app/json/"


def _clean_url(url: str) -> str:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.hostname not in _ALLOWED_HOSTS
    ):
        raise ValueError("Only verified public HTTPS source links can be exported")
    # Sources in this module are fixed, publicly documented endpoints.
    return url


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _obtain(
    path: Path,
    url: str,
    *,
    refresh: bool,
    max_age: timedelta,
    maximum: int = 12_000_000,
    allow_remote: bool = True,
) -> tuple[bytes, dict[str, Any]]:
    url = _clean_url(url)
    if path.exists() and (
        not refresh
        or (datetime.now(UTC).timestamp() - path.stat().st_mtime)
        < max_age.total_seconds()
    ):
        raw = path.read_bytes()
        origin = "local_cache"
    else:
        if not allow_remote:
            raise FileNotFoundError(
                f"Offline cache absent: {path}. Explicitly enable refresh if a download is intended."
            )
        req = Request(
            url,
            headers={
                "User-Agent": "OrbitobyScienceDay/0.2 research (local caching)",
                "Accept": "text/plain,text/csv,application/json,*/*",
            },
        )
        with urlopen(req, timeout=45) as response:
            raw = response.read(maximum + 1)
            if len(raw) > maximum:
                raise ValueError(f"Provider reply too large: {url}")
        if not raw.strip():
            raise ValueError(f"Provider returned empty file: {url}")
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_bytes(raw)
        temp.replace(path)
        origin = "remote_fetch"
    return raw, {
        "provider_url": url,
        "cache_file": path.name,
        "sha256": _digest(raw),
        "retrieved_at_utc": datetime.fromtimestamp(
            path.stat().st_mtime, UTC
        ).isoformat(),
        "cache_status": origin,
        "bytes": len(raw),
    }


def _norad(value: Any) -> int | None:
    try:
        n = int(str(value).strip())
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def _sat_raw(name: str, refresh: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ext, url, ttl = _SAT[name]
    path = _RAW_SAT / f"{name}.{ext}"
    # Prefer the user's verified immutable morning-batch raw copies when the cache is absent.
    if not path.exists() and not refresh:
        previous = sorted(
            _EVIDENCE.glob(f"{name}_*.{ext}"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if previous:
            path = previous[0]
    # STARLINK is already included in ACTIVE: do not fetch it redundantly.
    allow_remote = name != "starlink_gp"
    raw, record = _obtain(
        path,
        url,
        refresh=refresh,
        max_age=ttl,
        maximum=40_000_000,
        allow_remote=allow_remote,
    )
    if ext == "json":
        rows = json.loads(raw.decode("utf-8-sig"))
    else:
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    if (
        not isinstance(rows, list)
        or not rows
        or not all(isinstance(row, dict) for row in rows)
    ):
        raise ValueError(f"Malformed {name} satellite feed")
    if "NORAD_CAT_ID" not in rows[0]:
        raise ValueError(f"No NORAD_CAT_ID field in {name}")
    record.update(
        {
            "feed": name,
            "provider": "CelesTrak",
            "records": len(rows),
            "data_role": "catalog"
            if name == "satcat"
            else ("derived_supgp" if name == "spacex_supgp" else "gp_snapshot"),
        }
    )
    return rows, record


class SourceView:
    def __init__(self, source_rows: list[dict[str, Any]]):
        self._records = [dict(item) for item in source_rows]

    @property
    def table(self) -> pd.DataFrame:
        return pd.DataFrame(self._records)

    def show(self):
        print(
            self.table.to_string(index=False, max_colwidth=100)
            if self._records
            else "No source records."
        )
        return self

    def open(self, which: str | None = None) -> str:
        import webbrowser

        choices = self._records
        if which is not None:
            key = str(which).casefold()
            choices = [
                v
                for v in choices
                if key in str(v.get("feed", "")).casefold()
                or key in str(v.get("provider", "")).casefold()
            ]
        urls = sorted(
            {
                _clean_url(str(v.get("provider_url")))
                for v in choices
                if v.get("provider_url")
            }
        )
        if len(urls) != 1:
            raise ValueError(
                "Choose exactly one source using .sources().open('feed_name')"
            )
        webbrowser.open(urls[0])
        return urls[0]


class ResearchResult:
    def __init__(
        self,
        frame: pd.DataFrame,
        *,
        name: str,
        role: str,
        unit: str | None = None,
        sources: list[dict[str, Any]] | None = None,
        operations: list[dict[str, Any]] | None = None,
    ):
        self._frame = frame.copy()
        self.name = name
        self.role = role
        self.unit = unit
        self._sources = [dict(x) for x in (sources or [])]
        self._ops = list(operations or [])

    @property
    def table(self) -> pd.DataFrame:
        return self._frame.copy()

    def show(self, rows: int = 10):
        print(self._frame.head(rows).to_string(index=False))
        print(f"Rows: {len(self._frame):,} | {self.name} | {self.role}")
        return self

    def info(self):
        data = {
            "name": self.name,
            "role": self.role,
            "unit": self.unit,
            "rows": len(self._frame),
            "columns": list(self._frame.columns),
            "operations": self._ops,
            "sources": [
                {
                    "feed": v.get("feed"),
                    "sha256": v.get("sha256"),
                    "url": v.get("provider_url"),
                }
                for v in self._sources
            ],
        }
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
        return data

    def sources(self) -> SourceView:
        return SourceView(self._sources)

    def pick(self, *norad_ids: int):
        if "norad_id" not in self._frame:
            raise ValueError("pick() is only available on satellite tables")
        selected = {int(v) for v in norad_ids}
        unknown = selected - set(self._frame["norad_id"].dropna().astype(int))
        if unknown:
            raise ValueError(
                f"NORAD IDs not in the selected catalogue: {sorted(unknown)}"
            )
        frame = self._frame.loc[self._frame["norad_id"].isin(selected)].copy()
        return ResearchResult(
            frame,
            name=self.name,
            role=self.role,
            unit=self.unit,
            sources=self._sources_for_frame(frame),
            operations=[
                *self._ops,
                {"operation": "pick", "norad_ids": sorted(selected)},
            ],
        )

    def where(
        self,
        *,
        above: float | None = None,
        below: float | None = None,
        start: str | None = None,
        end: str | None = None,
    ):
        """Return a filtered copy; no filling, interpolation or mutation."""
        df = self._frame.copy()
        if above is not None or below is not None:
            if "value" not in df:
                raise ValueError("Value thresholds require a numeric 'value' column")
            numeric = pd.to_numeric(df["value"], errors="coerce")
            if above is not None:
                df = df.loc[numeric >= above]
                numeric = numeric.loc[df.index]
            if below is not None:
                df = df.loc[numeric <= below]
        if start is not None or end is not None:
            if "timestamp" not in df:
                raise ValueError("Date selection requires a timestamp column")
            time = pd.to_datetime(df["timestamp"], utc=True)
            if start is not None:
                df = df.loc[time >= pd.Timestamp(start, tz="UTC")]
                time = time.loc[df.index]
            if end is not None:
                df = df.loc[time < pd.Timestamp(end, tz="UTC")]
        op = {
            "operation": "where",
            "above_inclusive": above,
            "below_inclusive": below,
            "start_inclusive": start,
            "end_exclusive": end,
        }
        return ResearchResult(
            df,
            name=self.name,
            role=self.role,
            unit=self.unit,
            sources=self._sources_for_frame(df),
            operations=[*self._ops, op],
        )

    def save(self, filename: str | Path) -> Path:
        path = Path(filename)
        if path.suffix.lower() not in {".csv", ".parquet"}:
            raise ValueError("Research tables save as .csv or .parquet")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() == ".csv":
            self._frame.to_csv(path, index=False)
        else:
            self._frame.to_parquet(path, index=False)
        self._write_manifest(path)
        return path

    def _write_manifest(self, path: Path, *, plot: dict[str, Any] | None = None):
        payload = {
            "orbitoby_export": "science_day_v0.2",
            "created_utc": datetime.now(UTC).isoformat(),
            "name": self.name,
            "data_role": self.role,
            "unit": self.unit,
            "rows": len(self._frame),
            "operations": self._ops,
            "sources": self._sources,
            "export_file": path.name,
            "export_sha256": _digest(path.read_bytes()),
        }
        if plot:
            payload["plot"] = plot
        target = path.with_suffix(path.suffix + ".sources.json")
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return target

    def plot(
        self,
        *,
        highlight: tuple[str, str] | None = None,
        above: float | None = None,
        title: str | None = None,
        figsize: tuple[float, float] = (11, 4.8),
    ):
        if "timestamp" not in self._frame or "value" not in self._frame:
            raise ValueError(
                "This table has no unambiguous timestamp/value plot. Choose a scientific time series."
            )
        return ResearchFigure(
            self, highlight=highlight, above=above, title=title, figsize=figsize
        )

    def _sources_for_frame(self, frame):
        """Limit provenance to actual retained product rows or catalogue feeds."""
        if frame.empty:
            return []
        if "provider_url" in frame.columns:
            used_urls = set(frame["provider_url"].dropna().astype(str))
            return [
                dict(item)
                for item in self._sources
                if item.get("provider_url") in used_urls
            ]
        feeds = ("satcat", "active_gp", "starlink_gp", "spacex_supgp")
        if "norad_id" in frame.columns and any(f in frame.columns for f in feeds):
            used = {
                f
                for f in feeds
                if f in frame.columns and frame[f].fillna(False).astype(bool).any()
            }
            return [dict(item) for item in self._sources if item.get("feed") in used]
        return [dict(item) for item in self._sources]

    @property
    def ids(self):
        """Chosen NORAD identifiers, suitable for study.orbit(*selection.ids)."""
        if "norad_id" not in self._frame.columns:
            raise ValueError("ids is available only for satellite catalogue results")
        return tuple(int(value) for value in self._frame["norad_id"].dropna().unique())

    def find(self, query):
        """Select matching satellite names or an exact NORAD number."""
        if "norad_id" not in self._frame.columns or "name" not in self._frame.columns:
            raise ValueError("find() is available only for satellite catalogue results")
        if not isinstance(query, (int, str)) or not str(query).strip():
            raise ValueError(
                "Provide a satellite name or NORAD ID, for example 'STARLINK' or 39452"
            )
        text = str(query).strip()
        if text.isdecimal():
            matches = self._frame["norad_id"].eq(int(text))
        else:
            matches = (
                self._frame["name"]
                .fillna("")
                .astype(str)
                .str.contains(text, case=False, regex=False)
            )
        selected = self._frame.loc[matches].copy()
        if selected.empty:
            raise ValueError(f"No satellite catalogue match for {text!r}")
        return ResearchResult(
            selected,
            name=self.name,
            role=self.role,
            unit=self.unit,
            sources=self._sources_for_frame(selected),
            operations=[*self._ops, {"operation": "find", "query": text}],
        )

    def export(
        self, folder, *, plot=None, parquet=False, highlight=None, above=None, dpi=300
    ):
        """Save CSV, optional Parquet/PNG/SVG, and checksummed source manifests."""
        from pathlib import Path

        folder = Path(folder)
        if folder.exists() and any(folder.iterdir()):
            raise FileExistsError(
                f"Export folder is not empty: {folder}. Choose a new folder."
            )
        folder.mkdir(parents=True, exist_ok=True)
        self.save(folder / "data.csv")
        if parquet:
            self.save(folder / "data.parquet")
        supports_plot = (
            "timestamp" in self._frame.columns and "value" in self._frame.columns
        )
        if plot is None:
            plot = supports_plot
        if plot:
            if not supports_plot:
                raise ValueError(
                    "This table is not a time series. Use export(..., plot=False)."
                )
            chart = self.plot(highlight=highlight, above=above)
            chart.save(folder / "figure.svg", dpi=dpi)
            chart.save(folder / "figure.png", dpi=dpi)
        from datetime import UTC, datetime
        from hashlib import sha256
        from json import dumps

        files = sorted(item for item in folder.iterdir() if item.is_file())
        summary = {
            "schema": "orbitoby.science_day.bundle.v1",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "input_rows": len(self._frame),
            "data_role": self.role,
            "operations": list(self._ops),
            "sources": self._sources_for_frame(self._frame),
            "files": {f.name: sha256(f.read_bytes()).hexdigest() for f in files},
        }
        (folder / "bundle_manifest.json").write_text(
            dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
        return folder


class ResearchFigure:
    def __init__(
        self,
        result: ResearchResult,
        *,
        highlight: tuple[str, str] | None,
        above: float | None,
        title: str | None,
        figsize: tuple[float, float],
    ):
        self._result = result
        self.highlight = highlight
        self.above = above
        self.title = title or result.name
        self.figsize = figsize

    def sources(self) -> SourceView:
        return self._result.sources()

    def save(self, filename: str | Path, *, dpi: int = 300) -> Path:
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError as exc:
            raise ImportError(
                'Install plotting support: pip install "matplotlib>=3.8"'
            ) from exc
        path = Path(filename)
        if path.suffix.lower() not in {".png", ".svg"}:
            raise ValueError("Research figures save as .png or .svg")
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self._result.table
        x = pd.to_datetime(data["timestamp"], utc=True)
        y = pd.to_numeric(data["value"], errors="coerce")
        fig, ax = plt.subplots(figsize=self.figsize, layout="constrained")
        ax.plot(x, y, linewidth=0.9, label=self._result.name)
        if self.highlight is not None:
            start, end = self.highlight
            ax.axvspan(
                pd.Timestamp(start),
                pd.Timestamp(end),
                alpha=0.17,
                label="Selected period",
            )
        if self.above is not None:
            ax.scatter(
                x[y >= self.above],
                y[y >= self.above],
                s=8,
                label=f"Value >= {self.above}",
            )
            ax.axhline(self.above, linestyle="--", linewidth=0.7)
        ax.set_title(self.title)
        ax.set_ylabel(
            f"{self._result.name} ({self._result.unit})"
            if self._result.unit
            else self._result.name
        )
        ax.set_xlabel("Time (UTC)")
        ax.legend(loc="best")
        short_sources = ", ".join(
            f"{v.get('provider', 'Unknown')}:{v.get('feed', 'dataset')}"
            for v in self._result._sources
        )
        fig.text(
            0.01,
            0.003,
            f"Sources: {short_sources[:190]} | See .sources.json",
            fontsize=7,
        )
        settings = {
            "highlight_period": self.highlight,
            "above_inclusive": self.above,
            "dpi": dpi,
            "interpolation": "none",
            "resampling": "none",
        }
        try:
            fig.savefig(
                path,
                dpi=dpi,
                metadata={
                    "Description": json.dumps(
                        {"sources": self._result._sources, "plot": settings},
                        default=str,
                    )
                }
                if path.suffix.lower() == ".svg"
                else {"Description": "Orbitoby science day plot; see .sources.json"},
            )
        finally:
            plt.close(fig)
        self._result._write_manifest(path, plot=settings)
        return path


def catalog(group: str = "all", *, refresh: bool = False) -> ResearchResult:
    """Offline-first satellite catalogue. group: all, active, starlink, supgp.

    The union counts distinct NORAD IDs, not orbital epochs; cached snapshots may differ in age.
    """
    group = group.casefold().strip()
    if group not in {"all", "active", "starlink", "supgp"}:
        raise ValueError("group must be one of: all, active, starlink, supgp")
    names = ["satcat", "active_gp", "starlink_gp", "spacex_supgp"]
    rows_by_feed: dict[str, list[dict[str, Any]]] = {}
    records: list[dict[str, Any]] = []
    for name in names:
        try:
            rows, provenance = _sat_raw(
                name, refresh=refresh if name != "starlink_gp" else False
            )
            rows_by_feed[name] = rows
            records.append(provenance)
        except (FileNotFoundError, HTTPError, ValueError, TimeoutError, OSError) as exc:
            # The primary SATCAT/ACTIVE sources must not silently disappear.
            if name in {"satcat", "active_gp"}:
                raise RuntimeError(
                    f"Required CelesTrak source unavailable: {name}: {exc}"
                ) from exc
            # Optional prior STARLINK and SupGP feeds are separate products.
            print(f"Optional source not available: {name}: {exc}")
    merged: dict[int, dict[str, Any]] = {}
    for feed, rows in rows_by_feed.items():
        for record in rows:
            nid = _norad(record.get("NORAD_CAT_ID"))
            if nid is None:
                continue
            line = merged.setdefault(
                nid,
                {
                    "norad_id": nid,
                    "name": None,
                    "satcat": False,
                    "active_gp": False,
                    "starlink_gp": False,
                    "spacex_supgp": False,
                    "latest_epoch": None,
                },
            )
            line[feed] = True
            name = (
                record.get("OBJECT_NAME")
                or record.get("SATNAME")
                or record.get("OBJECT")
            )
            if name and (not line["name"] or feed == "satcat"):
                line["name"] = str(name)
            if feed == "active_gp" and record.get("EPOCH"):
                line["latest_epoch"] = record["EPOCH"]
    frame = pd.DataFrame(merged.values()).sort_values("norad_id").reset_index(drop=True)
    if group == "active":
        frame = frame.loc[frame["active_gp"]]
    elif group == "starlink":
        starlink_names = (
            frame["name"].fillna("").str.contains("STARLINK", case=False, regex=False)
        )
        frame = frame.loc[starlink_names | frame["starlink_gp"] | frame["spacex_supgp"]]
    elif group == "supgp":
        frame = frame.loc[frame["spacex_supgp"]]
    return ResearchResult(
        frame.reset_index(drop=True),
        name=f"CelesTrak {group} catalogue",
        role="catalogue_membership_not_orbital_history",
        sources=records,
        operations=[
            {"operation": "group", "selected": group, "refresh_requested": refresh}
        ],
    )


def _parse_nr_legacy(raw: bytes, source: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for line in raw.decode("utf-8-sig", errors="replace").splitlines():
        parts = [s.strip() for s in line.split(",")]
        if len(parts) < 8 or not re.fullmatch(r"(?:19|20)\d{2}", parts[2]):
            continue
        try:
            year, month, day = (int(parts[i]) for i in (2, 3, 4))
            observed = float(parts[5])
            adjusted = float(parts[6])
            stamp = datetime(year, month, day, tzinfo=UTC)
        except (ValueError, OverflowError):
            continue
        for label, value in (
            ("F10.7 observed", observed),
            ("F10.7 adjusted", adjusted),
        ):
            if value > 0:
                out.append(
                    {
                        "timestamp": stamp,
                        "value": value,
                        "metric": label,
                        "product": "historical_daily",
                        "time_semantics": "calendar_day_only",
                        "provider_url": source["provider_url"],
                    }
                )
    return out


def _parse_nr_modern(raw: bytes, source: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for line in raw.decode("utf-8-sig", errors="replace").splitlines():
        fields = line.split()
        if (
            len(fields) < 7
            or not re.fullmatch(r"\d{8}", fields[0])
            or not re.fullmatch(r"\d{6}", fields[1])
        ):
            continue
        try:
            dt = datetime.strptime(fields[0] + fields[1], "%Y%m%d%H%M%S").replace(
                tzinfo=UTC
            )
            observed, adjusted = float(fields[4]), float(fields[5])
        except ValueError:
            continue
        for label, value in (
            ("F10.7 observed", observed),
            ("F10.7 adjusted", adjusted),
        ):
            if value > 0:
                out.append(
                    {
                        "timestamp": dt,
                        "value": value,
                        "metric": label,
                        "product": "modern_three_daily_readings",
                        "time_semantics": "measured_utc",
                        "provider_url": source["provider_url"],
                    }
                )
    return out


def _parse_nr_bridge(raw: bytes, source: dict[str, Any]) -> list[dict[str, Any]]:
    # The legacy bridge format is different from the modern and 1947-1996 files.
    # Recognise only explicitly parseable year/month/day + observed/adjusted records;
    # do not fill any gaps or guess columns on an unfamiliar provider revision.
    out = []
    for line in raw.decode("utf-8-sig", errors="replace").splitlines():
        fields = line.split()
        # Explicit bridge convention commonly includes Julian day + rotation + YYYY MM DD HHMM OBS ADJ ...
        if len(fields) < 8:
            continue
        if not (
            re.fullmatch(r"(?:19|20)\d{2}", fields[2])
            and re.fullmatch(r"\d{1,2}", fields[3])
            and re.fullmatch(r"\d{1,2}", fields[4])
        ):
            continue
        try:
            date = datetime(int(fields[2]), int(fields[3]), int(fields[4]), tzinfo=UTC)
            observed = float(fields[6])
            adjusted = float(fields[7])
        except (ValueError, OverflowError):
            continue
        for label, val in (("F10.7 observed", observed), ("F10.7 adjusted", adjusted)):
            if val > 0:
                out.append(
                    {
                        "timestamp": date,
                        "value": val,
                        "metric": label,
                        "product": "bridge_daily",
                        "time_semantics": "calendar_day_only",
                        "provider_url": source["provider_url"],
                    }
                )
    return out


def _parse_silso(raw: bytes, source: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for row in csv.reader(io.StringIO(raw.decode("utf-8-sig")), delimiter=";"):
        if len(row) < 4:
            continue
        try:
            year, month = int(row[0]), int(row[1])
            number = float(row[3])
            status = str(row[6]).strip() if len(row) > 6 else "unknown"
            date = datetime(year, month, 1, tzinfo=UTC)
        except (ValueError, OverflowError):
            continue
        if number >= 0:
            out.append(
                {
                    "timestamp": date,
                    "value": number,
                    "metric": "SSN smoothed monthly",
                    "product": "SILSO_V2_monthly_smoothed",
                    "time_semantics": "month_bucket",
                    "status": status,
                    "provider_url": source["provider_url"],
                }
            )
    return out


def _gfz_history(
    metric: str, start: str, end: str, *, refresh: bool
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    # The provider explicitly documents `datetime`, the requested index and status in JSON.
    requested = {"Kp": "Kp", "ap": "ap", "Ap": "Ap"}[metric]
    a, b = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
    if not a < b:
        raise ValueError("End date must be later than start date")
    observations, receipts = [], []
    current = a
    while current < b:
        next_date = min(current + pd.Timedelta(days=366), b)
        # Endpoint `end` is inclusive, so cut one second from exclusive API end.
        params = urlencode(
            {
                "start": current.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end": (next_date - pd.Timedelta(seconds=1)).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                "index": requested,
            }
        )
        url = f"{_GFZ}?{params}"
        filename = (
            _RAW_SOLAR
            / f"gfz_{requested}_{current.strftime('%Y%m%d')}_{next_date.strftime('%Y%m%d')}.json"
        )
        raw, receipt = _obtain(
            filename, url, refresh=refresh, max_age=timedelta(days=3), maximum=6_000_000
        )
        receipt.update(
            {
                "provider": "GFZ Potsdam",
                "feed": f"GFZ {metric}",
                "data_role": "geomagnetic_index",
            }
        )
        obj = json.loads(raw)
        times, values = obj.get("datetime"), obj.get(requested)
        statuses = obj.get("status", [])
        if (
            not isinstance(times, list)
            or not isinstance(values, list)
            or len(times) != len(values)
        ):
            raise ValueError(f"GFZ API response missing requested {requested} series")
        for index, (timestamp, value) in enumerate(zip(times, values)):
            if value is None:
                continue
            try:
                when = pd.to_datetime(timestamp, utc=True)
                val = float(value)
            except (ValueError, TypeError):
                continue
            observations.append(
                {
                    "timestamp": when,
                    "value": val,
                    "metric": metric,
                    "status": str(statuses[index])
                    if index < len(statuses)
                    else "unknown",
                    "provider_url": receipt["provider_url"],
                    "product": requested,
                    "time_semantics": "provider_index_interval_start",
                }
            )
        receipts.append(receipt)
        current = next_date
    return observations, receipts


def solar_history(
    metric: str, start: str, end: str, *, refresh: bool = False
) -> ResearchResult:
    """Historical official solar/geomagnetic series, without interpolation.

    F10.7 uses NRCan files; SSN uses SILSO; Kp/ap/Ap use GFZ web service.
    Date selection uses UTC half-open [start,end). No implicit source blending.
    """
    aliases = {
        "f10.7": "F10.7 observed",
        "f107": "F10.7 observed",
        "f10.7 observed": "F10.7 observed",
        "f10.7 adjusted": "F10.7 adjusted",
        "ssn": "SSN smoothed monthly",
        "sunspots": "SSN smoothed monthly",
        "ssn smoothed monthly": "SSN smoothed monthly",
        "kp": "Kp",
        "ap (3h)": "ap",
        "daily ap": "Ap",
    }
    key = aliases.get(str(metric).strip().casefold())
    if key is None:
        raise ValueError(
            "Known metrics: F10.7, F10.7 adjusted, SSN, Kp, ap (3h), daily Ap. Dst continues via existing study.weather('Dst')."
        )
    first, last = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
    if not first < last:
        raise ValueError("End date must be after start date")
    unit = (
        "sfu"
        if key.startswith("F10.7")
        else (
            "index"
            if key.startswith("SSN") or key == "Kp"
            else "nT-independent ap units"
        )
    )
    observations, receipts = [], []
    if key.startswith("F10.7"):
        for name, url in _F107.items():
            path = _RAW_SOLAR / f"nrcan_f107_{name}.txt"
            raw, receipt = _obtain(
                path,
                url,
                refresh=refresh,
                max_age=timedelta(days=1 if name == "modern" else 365),
            )
            receipt.update(
                {
                    "provider": "NRCan Canada",
                    "feed": f"NRCan F10.7 {name}",
                    "data_role": "measured_radio_flux",
                    "unit": "sfu",
                }
            )
            parser = {
                "historic": _parse_nr_legacy,
                "bridge": _parse_nr_bridge,
                "modern": _parse_nr_modern,
            }[name]
            parsed = parser(raw, receipt)
            if name == "bridge" and not parsed:
                print(
                    "NOTE: NRCan 1996-2007 bridge layout not recognised; no data invented for this period."
                )
            observations.extend(r for r in parsed if r["metric"] == key)
            receipts.append(receipt)
    elif key.startswith("SSN"):
        raw, receipt = _obtain(
            _RAW_SOLAR / "silso_smoothed_monthly_v2.csv",
            _SILSO,
            refresh=refresh,
            max_age=timedelta(days=7),
        )
        receipt.update(
            {
                "provider": "WDC-SILSO",
                "feed": "SILSO SSN monthly smoothed V2",
                "data_role": "processed_sunspot_index",
                "unit": "index",
                "license": "CC BY-NC 4.0",
            }
        )
        observations.extend(_parse_silso(raw, receipt))
        receipts.append(receipt)
    else:
        observations, receipts = _gfz_history(key, start, end, refresh=refresh)
    if not observations:
        raise ValueError(
            "No usable official observations found; source formats or coverage may have changed"
        )
    table = pd.DataFrame(observations)
    table["timestamp"] = pd.to_datetime(table["timestamp"], utc=True)
    table = table.loc[
        (table["timestamp"] >= first) & (table["timestamp"] < last)
    ].copy()
    # When daily products overlap three-per-day measurements, choose ONE
    # product family per UTC calendar day, preserving every modern reading.
    # Resolving only identical timestamps would incorrectly combine legacy
    # placeholder midnight records with actual modern measurement times.
    table["_priority"] = (
        table["product"]
        .map(
            {"modern_three_daily_readings": 3, "bridge_daily": 2, "historical_daily": 1}
        )
        .fillna(0)
    )
    table["_day"] = table["timestamp"].dt.floor("D")
    best = table.groupby(["metric", "_day"], dropna=False)["_priority"].transform("max")
    table = table.loc[table["_priority"].eq(best)].copy()
    table = table.sort_values(["timestamp", "_priority"], ascending=[True, False])
    table = table.drop_duplicates(subset=["metric", "timestamp"], keep="first")
    table = table.drop(columns=["_priority", "_day"])
    table = table.sort_values("timestamp").reset_index(drop=True)
    # Source lineage must describe records actually retained in this result,
    # not every provider file that happened to be inspected during the query.
    contributing_urls = set(table["provider_url"].dropna())
    receipts = [item for item in receipts if item["provider_url"] in contributing_urls]
    if table.empty:
        raise ValueError("No observations in selected period (UTC half-open range)")
    return ResearchResult(
        table,
        name=key,
        role="measurement" if key.startswith("F10.7") else "derived_geophysical_index",
        unit=unit,
        sources=receipts,
        operations=[
            {
                "operation": "date_range",
                "start_inclusive": start,
                "end_exclusive": end,
                "duplicate_policy": "one preferred source product per UTC day; preserve individual modern readings; no interpolation",
            }
        ],
    )
