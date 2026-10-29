# ============================================================================
#                     ,/|  _.-''''-._      ~  JAI  SHARMA  ~
#                    //,'.'   _   _  '.
#                   // / /  _( o )_( o)_\       SURVIVAL DRAGON
#                  //,'/ /  /   ~    ~   \_
#                 // /,'/   \   \____/    \'-.    ~ 24-month P(alive) ~
#                //,'/,'     '._,'    '.___\  '-.
#               // /          ___                '-.___
#              //,'          /   \                     '-.
#             //         ___/     \___       )))))         '-.___
#            /'       __/             \___________________________\
#           '        /                     ~ built by Jai Sharma ~  \
#                   /_______________________________________________/
# ============================================================================
"""Survival model: given features at time T, predict P(a new restaurant here
survives 24 months).

Training data construction:
  * From the inspections file, each unique business gets a 'first_seen' and
    'last_seen' date. A business whose last_seen is more than 180 days before
    the file's max date is considered 'closed'.
  * For every business, we snapshot the block-group features and label it
    survived=1 if (last_seen - first_seen) >= 24 months, else 0.
  * Train a LightGBM classifier predicting survived.

The classifier's `predict_proba` on a candidate BG + proposed cuisine gives
the 24-month survival probability.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import joblib
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, average_precision_score
from config.settings import DATA_RAW, DATA_PROCESSED

SURV_WINDOW_DAYS = 365 * 2
CLOSED_IF_SILENT_DAYS = 180

FEATURES = [
    "pop_density", "median_age", "median_income",
    "pct_students", "pct_white", "pct_black", "pct_asian", "pct_hispanic",
    "daytime_pop", "daytime_ratio", "jobs_food_accom",
    "restaurant_count", "cuisine_diversity", "saturation_index",
    "critical_rate", "failure_rate",
]


@dataclass
class SurvivalHP:
    n_estimators: int = 500
    learning_rate: float = 0.05
    num_leaves: int = 31
    min_child_samples: int = 20
    reg_lambda: float = 0.2
    random_state: int = 42


def _build_business_lifecycle() -> pd.DataFrame:
    insp = pd.read_parquet(DATA_RAW / "boston_food_inspections.parquet")
    cols = {c.lower(): c for c in insp.columns}

    def pick(*names):
        for n in names:
            if n in cols:
                return cols[n]
        return None

    biz = pick("businessname", "dbaname", "name")
    lat = pick("property_latitude", "latitude", "lat")
    lon = pick("property_longitude", "longitude", "lon")
    loc = pick("location")
    date = pick("violation_date", "violdttm", "resultdttm")
    if not (biz and date):
        raise RuntimeError("inspections file missing required columns")

    if not (lat and lon) and loc:
        parsed = insp[loc].astype(str).str.extract(r"\(?\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*\)?")
        insp = insp.assign(lat=pd.to_numeric(parsed[0], errors="coerce"),
                           lon=pd.to_numeric(parsed[1], errors="coerce"))
        lat, lon = "lat", "lon"

    df = insp[[biz, lat, lon, date]].copy()
    df.columns = ["business", "lat", "lon", "date"]
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True).dt.tz_localize(None)
    df = df.dropna(subset=["business", "lat", "lon", "date"])

    life = df.groupby("business").agg(
        first_seen=("date", "min"),
        last_seen=("date", "max"),
        lat=("lat", "mean"),
        lon=("lon", "mean"),
    ).reset_index()

    file_max = df["date"].max()
    life["closed"] = (file_max - life["last_seen"]).dt.days > CLOSED_IF_SILENT_DAYS
    life["lifespan_days"] = (life["last_seen"] - life["first_seen"]).dt.days
    life["survived_24mo"] = (life["lifespan_days"] >= SURV_WINDOW_DAYS).astype(int)
    return life


def train(hp: SurvivalHP | None = None):
    hp = hp or SurvivalHP()
    life = _build_business_lifecycle()

    import geopandas as gpd
    from shapely.geometry import Point
    from src.features.build import _load_blockgroups_gdf

    bg = _load_blockgroups_gdf()
    pts = gpd.GeoDataFrame(
        life,
        geometry=[Point(xy) for xy in zip(life["lon"], life["lat"])],
        crs=4326,
    )
    joined = gpd.sjoin(pts, bg, predicate="within", how="left").dropna(subset=["geoid"])

    feats = pd.read_parquet(DATA_PROCESSED / "predictions.parquet")
    df = joined.merge(feats[["geoid"] + [c for c in FEATURES if c in feats.columns]],
                      on="geoid", how="left")
    df = df.dropna(subset=["survived_24mo"] + [c for c in FEATURES if c in df.columns])

    X = df[[c for c in FEATURES if c in df.columns]]
    y = df["survived_24mo"]
    if len(X) < 200:
        print(f"[warn] only {len(X)} samples; survival model may be unreliable")

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=hp.random_state, stratify=y)
    model = lgb.LGBMClassifier(
        n_estimators=hp.n_estimators,
        learning_rate=hp.learning_rate,
        num_leaves=hp.num_leaves,
        min_child_samples=hp.min_child_samples,
        reg_lambda=hp.reg_lambda,
        random_state=hp.random_state,
        verbose=-1,
    )
    model.fit(X_tr, y_tr)
    p_te = model.predict_proba(X_te)[:, 1]
    auc = roc_auc_score(y_te, p_te) if y_te.nunique() > 1 else float("nan")
    ap = average_precision_score(y_te, p_te) if y_te.nunique() > 1 else float("nan")
    print(f"survival model: AUC={auc:.3f}  AP={ap:.3f}  n_train={len(X_tr)}")

    out = DATA_PROCESSED / "survival_model.joblib"
    joblib.dump({"model": model, "features": list(X.columns), "auc": auc, "ap": ap}, out)
    (DATA_PROCESSED / "survival_hp.json").write_text(json.dumps(asdict(hp), indent=2))
    print(f"wrote survival model → {out}")
    return model


def predict_survival(block_group_row: dict) -> float:
    bundle = joblib.load(DATA_PROCESSED / "survival_model.joblib")
    model, feats = bundle["model"], bundle["features"]
    X = pd.DataFrame([{f: block_group_row.get(f, 0) for f in feats}])
    return float(model.predict_proba(X)[0, 1])


if __name__ == "__main__":
    train()
