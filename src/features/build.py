"""Join demographics + restaurants into one block-group-level feature table.

Steps:
  1. Load ACS block groups (demographics).
  2. Load Boston block-group polygons (TIGER/Line) OR approximate by snapping
     restaurants to the nearest tract via a bundled centroid table.
  3. Point-in-polygon → every restaurant gets a geoid.
  4. Aggregate restaurant counts, cuisine diversity, violation rates per BG.
  5. Compute density, saturation inputs.
"""
from __future__ import annotations
import math
from pathlib import Path
import pandas as pd
import numpy as np
from config.settings import DATA_RAW, DATA_PROCESSED

TIGER_BG_URL = (
    "https://www2.census.gov/geo/tiger/TIGER2022/BG/tl_2022_25_bg.zip"
)


def _load_blockgroups_gdf():
    """Lazy import geopandas; download TIGER shapefile on first run."""
    import geopandas as gpd
    local = DATA_RAW / "tl_2022_25_bg.zip"
    if not local.exists():
        import requests
        print("downloading TIGER block-group shapefile …")
        r = requests.get(TIGER_BG_URL, timeout=180)
        local.write_bytes(r.content)
    gdf = gpd.read_file(f"zip://{local}")
    gdf = gdf[gdf["COUNTYFP"] == "025"].copy()
    gdf["geoid"] = gdf["GEOID"]
    return gdf.to_crs(4326)[["geoid", "ALAND", "geometry"]]


def _shannon(series: pd.Series) -> float:
    counts = series.dropna().value_counts()
    if counts.empty:
        return 0.0
    p = counts / counts.sum()
    return float(-(p * np.log(p)).sum())


def build_features() -> pd.DataFrame:
    import geopandas as gpd
    from shapely.geometry import Point

    acs = pd.read_parquet(DATA_RAW / "census_acs_blockgroups.parquet")
    osm = pd.read_parquet(DATA_RAW / "osm_restaurants.parquet")

    bg = _load_blockgroups_gdf()
    pts = gpd.GeoDataFrame(
        osm,
        geometry=[Point(xy) for xy in zip(osm["lon"], osm["lat"])],
        crs=4326,
    )
    joined = gpd.sjoin(pts, bg, predicate="within", how="left")

    agg = joined.groupby("geoid").agg(
        restaurant_count=("osm_id", "count"),
        cuisine_diversity=("cuisine", _shannon),
        fast_food_count=("amenity", lambda s: (s == "fast_food").sum()),
        cafe_count=("amenity", lambda s: (s == "cafe").sum()),
    ).reset_index()

    feats = acs.merge(agg, on="geoid", how="left").fillna({"restaurant_count": 0, "cuisine_diversity": 0})

    land_km2 = bg[["geoid", "ALAND"]].copy()
    land_km2["land_km2"] = land_km2["ALAND"] / 1_000_000
    feats = feats.merge(land_km2[["geoid", "land_km2"]], on="geoid", how="left")

    feats["pop_density"] = feats["total_pop"] / feats["land_km2"].replace(0, np.nan)
    feats["restaurants_per_1000"] = (
        feats["restaurant_count"] / feats["total_pop"].replace(0, np.nan) * 1000
    )

    lodes_path = DATA_RAW / "lodes_wac_by_bg.parquet"
    if lodes_path.exists():
        lodes = pd.read_parquet(lodes_path)
        feats = feats.merge(lodes, on="geoid", how="left")
        feats[["jobs_total", "jobs_food_accom", "jobs_retail", "jobs_high_wage"]] = (
            feats[["jobs_total", "jobs_food_accom", "jobs_retail", "jobs_high_wage"]].fillna(0)
        )
        feats["daytime_pop"] = feats["total_pop"].fillna(0) + feats["jobs_total"]
        feats["daytime_ratio"] = feats["daytime_pop"] / feats["total_pop"].replace(0, np.nan)
    else:
        feats["jobs_total"] = 0
        feats["daytime_pop"] = feats["total_pop"]
        feats["daytime_ratio"] = 1.0

    viol_path = DATA_PROCESSED / "violations_by_bg.parquet"
    if viol_path.exists():
        viol = pd.read_parquet(viol_path)
        feats = feats.merge(viol[["geoid", "critical_rate", "failure_rate", "inspections_24mo"]],
                            on="geoid", how="left")
        feats[["critical_rate", "failure_rate", "inspections_24mo"]] = (
            feats[["critical_rate", "failure_rate", "inspections_24mo"]].fillna(0)
        )
    else:
        feats["critical_rate"] = 0.0
        feats["failure_rate"] = 0.0
        feats["inspections_24mo"] = 0

    out = DATA_PROCESSED / "features.parquet"
    feats.to_parquet(out)
    print(f"wrote feature table ({len(feats)} rows, {feats.shape[1]} cols) → {out}")
    return feats


if __name__ == "__main__":
    build_features()
