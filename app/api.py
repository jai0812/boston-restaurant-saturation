# ============================================================================
#                        ___          ___
#                       /   \__    __/   \      ~  JAI  SHARMA  ~
#                      /       \  /       \
#                      |  (o)  _\/_  (o)  |         API  DRAGON
#                       \     /    \     /
#                        \   / FAST \   /       ~  guards every route  ~
#                         \_/  API   \_/
#                          |          |
#                          |  BOSTON  |            /\/\/\/\/\/\
#                          |   8000   |__________/              \
#                          |__________|   ))))))                 \
#                                                 \_______________\
#                                                   ~ Jai Sharma ~
# ============================================================================
"""FastAPI service exposing the saturation + survival + cuisine models.

Run:
    uvicorn app.api:app --reload --port 8000
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import math
import pandas as pd
import joblib
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from config.settings import DATA_PROCESSED

app = FastAPI(title="Boston Restaurant Saturation API", version="0.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def _preds() -> pd.DataFrame:
    return pd.read_parquet(DATA_PROCESSED / "predictions.parquet")


@lru_cache(maxsize=1)
def _cuisines() -> pd.DataFrame:
    p = DATA_PROCESSED / "cuisine_recs.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


@lru_cache(maxsize=1)
def _survival_bundle():
    return joblib.load(DATA_PROCESSED / "survival_model.joblib")


@lru_cache(maxsize=1)
def _bg_centroids():
    from src.features.build import _load_blockgroups_gdf
    bg = _load_blockgroups_gdf()
    bg["cx"] = bg.geometry.centroid.x
    bg["cy"] = bg.geometry.centroid.y
    return bg[["geoid", "cx", "cy"]]


def _nearest_geoid(lat: float, lon: float) -> str:
    bg = _bg_centroids()
    d = (bg["cx"] - lon) ** 2 + (bg["cy"] - lat) ** 2
    return bg.loc[d.idxmin(), "geoid"]


class BlockGroupOut(BaseModel):
    geoid: str
    total_pop: float | None
    median_income: float | None
    restaurant_count: int
    recommended_min: float
    recommended_max: float
    saturation_index: float | None
    risk_flag: str


class WhatIfIn(BaseModel):
    lat: float
    lon: float
    cuisine: str | None = None
    cannibalization_radius_m: float = 500


class WhatIfOut(BaseModel):
    geoid: str
    survival_probability: float
    saturation_before: float
    saturation_after: float
    cuisine_fit: float
    cannibalized_restaurants: int
    verdict: str


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/stats")
def stats():
    df = _preds()
    return {
        "block_groups": int(len(df)),
        "restaurants_total": int(df["restaurant_count"].sum()),
        "oversaturated": int((df["risk_flag"] == "oversaturated").sum()),
        "underserved": int((df["risk_flag"] == "underserved").sum()),
    }


@app.get("/blockgroups", response_model=list[BlockGroupOut])
def list_bgs(risk: str | None = None, limit: int = Query(500, le=5000)):
    df = _preds()
    if risk:
        df = df[df["risk_flag"] == risk]
    out = df[["geoid", "total_pop", "median_income", "restaurant_count",
              "recommended_min", "recommended_max", "saturation_index", "risk_flag"]]
    return out.head(limit).to_dict(orient="records")


@app.get("/blockgroup/{geoid}")
def one_bg(geoid: str):
    df = _preds()
    row = df[df["geoid"] == geoid]
    if row.empty:
        raise HTTPException(404, "unknown geoid")
    rec = row.iloc[0].to_dict()
    cui = _cuisines()
    if not cui.empty:
        c = cui[cui["geoid"] == geoid]
        if not c.empty:
            rec["recommended_cuisines"] = c.iloc[0]["recommended_cuisines"]
            rec["target_mix"] = c.iloc[0]["target_mix"]
    return rec


@app.post("/whatif", response_model=WhatIfOut)
def whatif(body: WhatIfIn):
    df = _preds()
    geoid = _nearest_geoid(body.lat, body.lon)
    row = df[df["geoid"] == geoid]
    if row.empty:
        raise HTTPException(404, "no features for this location")
    row = row.iloc[0]

    sat_before = float(row["saturation_index"] or 0)
    recommended = max(float(row["recommended_mid"]), 1e-6)
    sat_after = (float(row["restaurant_count"]) + 1) / recommended

    try:
        bundle = _survival_bundle()
        X = pd.DataFrame([{f: row.get(f, 0) for f in bundle["features"]}])
        X.loc[:, "saturation_index"] = sat_after
        p_surv = float(bundle["model"].predict_proba(X)[0, 1])
    except FileNotFoundError:
        p_surv = max(0.0, min(1.0, 1.0 - sat_after / 2))

    cuisine_fit = 0.5
    cui = _cuisines()
    if body.cuisine and not cui.empty:
        c = cui[cui["geoid"] == geoid]
        if not c.empty:
            gaps = c.iloc[0]["recommended_cuisines"] or {}
            if body.cuisine in gaps:
                g = gaps.get(body.cuisine) or 0.0
                cuisine_fit = max(0.0, min(1.0, (float(g) + 0.2) / 0.4))

    cann = _cannibalization(body.lat, body.lon, body.cannibalization_radius_m)

    if p_surv > 0.65 and sat_after < 1.1 and cuisine_fit > 0.4:
        verdict = "go"
    elif p_surv < 0.4 or sat_after > 1.3:
        verdict = "avoid"
    else:
        verdict = "risky"

    return WhatIfOut(
        geoid=geoid,
        survival_probability=round(p_surv, 3),
        saturation_before=round(sat_before, 3),
        saturation_after=round(sat_after, 3),
        cuisine_fit=round(cuisine_fit, 3),
        cannibalized_restaurants=cann,
        verdict=verdict,
    )


def _cannibalization(lat: float, lon: float, radius_m: float) -> int:
    try:
        osm = pd.read_parquet(Path("data/raw/osm_restaurants.parquet"))
    except FileNotFoundError:
        return 0
    R = 6371000
    import numpy as np
    phi1 = math.radians(lat)
    phi2 = np.radians(osm["lat"].values)
    dphi = np.radians(osm["lat"].values - lat)
    dlam = np.radians(osm["lon"].values - lon)
    a = np.sin(dphi / 2) ** 2 + math.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    d = 2 * R * np.arcsin(np.sqrt(a))
    return int((d <= radius_m).sum())
