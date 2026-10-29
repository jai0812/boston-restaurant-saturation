"""Aggregate Boston food-inspection records into per-business risk scores,
then roll up to the block-group level so the capacity model can learn
from real hygiene signal instead of a density proxy.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from config.settings import DATA_RAW, DATA_PROCESSED

CRITICAL_LEVELS = {"***", "**", "*"}


def _norm_level(x) -> str:
    if pd.isna(x):
        return ""
    s = str(x).strip()
    return s


def build_violation_features() -> pd.DataFrame:
    insp_path = DATA_RAW / "boston_food_inspections.parquet"
    if not insp_path.exists():
        print("[warn] no inspections file; skipping violation features")
        return pd.DataFrame()

    insp = pd.read_parquet(insp_path)
    cols = {c.lower(): c for c in insp.columns}

    def pick(*names):
        for n in names:
            if n in cols:
                return cols[n]
        return None

    biz = pick("businessname", "dbaname", "name")
    addr = pick("address", "location_street_num")
    lat = pick("property_latitude", "latitude", "lat")
    lon = pick("property_longitude", "longitude", "lon")
    loc = pick("location")
    level = pick("violation_level", "viol_level", "violationlevel")
    date = pick("violation_date", "violdttm", "resultdttm")
    status = pick("violation_status", "viol_status", "violstatus", "result")

    if not (lat and lon) and loc:
        parsed = insp[loc].astype(str).str.extract(r"\(?\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*\)?")
        insp["lat"] = pd.to_numeric(parsed[0], errors="coerce")
        insp["lon"] = pd.to_numeric(parsed[1], errors="coerce")
        lat, lon = "lat", "lon"

    if not (lat and lon):
        print("[warn] inspections missing lat/lon columns; skipping")
        return pd.DataFrame()

    insp = insp[[c for c in [biz, addr, lat, lon, level, date, status] if c]].copy()
    insp.columns = ["business", "address", "lat", "lon", "level", "date", "status"][: insp.shape[1]]
    insp["lat"] = pd.to_numeric(insp["lat"], errors="coerce")
    insp["lon"] = pd.to_numeric(insp["lon"], errors="coerce")
    insp["date"] = pd.to_datetime(insp["date"], errors="coerce", utc=True).dt.tz_localize(None)
    insp = insp.dropna(subset=["lat", "lon", "date"])

    cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=365 * 2)
    recent = insp[insp["date"] >= cutoff].copy()
    recent["is_critical"] = recent["level"].apply(_norm_level).isin(CRITICAL_LEVELS)
    recent["is_fail"] = recent.get("status", pd.Series(dtype=str)).astype(str).str.lower().str.contains("fail|unsat", na=False)

    import geopandas as gpd
    from shapely.geometry import Point
    from src.features.build import _load_blockgroups_gdf

    bg = _load_blockgroups_gdf()
    pts = gpd.GeoDataFrame(
        recent,
        geometry=[Point(xy) for xy in zip(recent["lon"], recent["lat"])],
        crs=4326,
    )
    joined = gpd.sjoin(pts, bg, predicate="within", how="left")

    agg = joined.groupby("geoid").agg(
        inspections_24mo=("business", "count"),
        critical_violations=("is_critical", "sum"),
        failures=("is_fail", "sum"),
        unique_biz=("business", "nunique"),
    ).reset_index()

    agg["critical_rate"] = agg["critical_violations"] / agg["inspections_24mo"].replace(0, np.nan)
    agg["failure_rate"] = agg["failures"] / agg["inspections_24mo"].replace(0, np.nan)

    out = DATA_PROCESSED / "violations_by_bg.parquet"
    agg.to_parquet(out)
    print(f"wrote violation features ({len(agg)} BGs) → {out}")
    return agg


if __name__ == "__main__":
    build_violation_features()
