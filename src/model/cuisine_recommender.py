"""Recommend an underserved cuisine mix for each block group.

Approach: for the target BG, find k nearest neighbors in demographic space
among healthy BGs. Average their cuisine distribution → 'target_mix'.
Compare to actual mix in the target BG → recommend what's underrepresented.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
from config.settings import DATA_RAW, DATA_PROCESSED

DEMO_FEATURES = [
    "median_income", "median_age", "pct_students",
    "pct_white", "pct_black", "pct_asian", "pct_hispanic",
]


def _cuisine_matrix() -> pd.DataFrame:
    osm = pd.read_parquet(DATA_RAW / "osm_restaurants.parquet")
    feats = pd.read_parquet(DATA_PROCESSED / "features.parquet")

    import geopandas as gpd
    from shapely.geometry import Point
    from src.features.build import _load_blockgroups_gdf
    bg = _load_blockgroups_gdf()
    pts = gpd.GeoDataFrame(
        osm,
        geometry=[Point(xy) for xy in zip(osm["lon"], osm["lat"])],
        crs=4326,
    )
    joined = gpd.sjoin(pts, bg, predicate="within", how="left")
    joined = joined.dropna(subset=["cuisine"])
    joined["cuisine_main"] = joined["cuisine"].str.split(";").str[0]

    mat = (
        joined.groupby(["geoid", "cuisine_main"]).size()
        .unstack(fill_value=0)
    )
    mat = mat.div(mat.sum(axis=1), axis=0)
    return mat


def recommend(k: int = 15) -> pd.DataFrame:
    feats = pd.read_parquet(DATA_PROCESSED / "predictions.parquet").dropna(subset=DEMO_FEATURES)
    cuisines = _cuisine_matrix()

    healthy = feats[feats["risk_flag"] == "balanced"].set_index("geoid")
    healthy_cui = cuisines.reindex(healthy.index).fillna(0)

    scaler = StandardScaler()
    Xh = scaler.fit_transform(healthy[DEMO_FEATURES])
    nn = NearestNeighbors(n_neighbors=min(k, len(Xh))).fit(Xh)

    all_X = scaler.transform(feats[DEMO_FEATURES])
    dists, idx = nn.kneighbors(all_X)

    rows = []
    for i, geoid in enumerate(feats["geoid"]):
        neigh = healthy_cui.iloc[idx[i]].mean(axis=0)
        actual = cuisines.loc[geoid] if geoid in cuisines.index else pd.Series(dtype=float)
        actual = actual.reindex(neigh.index).fillna(0)
        gap = neigh - actual
        top_rec = gap.sort_values(ascending=False).head(5)
        rows.append({
            "geoid": geoid,
            "recommended_cuisines": top_rec.to_dict(),
            "target_mix": neigh.sort_values(ascending=False).head(5).to_dict(),
        })

    out = pd.DataFrame(rows)
    out.to_parquet(DATA_PROCESSED / "cuisine_recs.parquet")
    print(f"wrote cuisine recommendations → {DATA_PROCESSED/'cuisine_recs.parquet'}")
    return out


if __name__ == "__main__":
    recommend()
