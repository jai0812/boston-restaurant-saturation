# ============================================================================
#              __                                                       __
#             /  \__                                                 __/  \
#            /      \_      ~  JAI  SHARMA  ·  DRAGON  ~          _/      \
#            |   /\   \__                                      __/   /\   |
#             \ ( o )     \__       ___       ___       __    /    ( o ) /
#              '--'          \_   _/   \_   _/   \_   _/  \__/      '--'
#                              \_/       \_/       \_/
#                              /                        \
#                             /    CAPACITY  MODEL       \
#                            /       Boston · 2026        \
#                           /______________________________\
#                                      ~ Jai Sharma ~
# ============================================================================
"""Predict the healthy restaurant count for a block group.

Training target: restaurants_per_1000 on 'healthy' block groups
(we define healthy as those below the city-wide 75th percentile of
cuisine_diversity-adjusted density — a crude proxy until violation data
is joined). Residual sigma gives the ± band.

Model: LightGBM regressor with sklearn API. Tunable hyperparameters are
exposed via the HyperParams dataclass.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import KFold, cross_val_predict
import lightgbm as lgb
from config.settings import DATA_PROCESSED

FEATURES = [
    "pop_density", "median_age", "median_income",
    "pct_students", "pct_white", "pct_black", "pct_asian", "pct_hispanic",
    "avg_hh_size", "households", "land_km2",
    "daytime_pop", "daytime_ratio", "jobs_food_accom", "jobs_high_wage",
]

TARGET = "restaurants_per_1000"


@dataclass
class HyperParams:
    n_estimators: int = 400
    learning_rate: float = 0.05
    num_leaves: int = 31
    min_child_samples: int = 10
    reg_lambda: float = 0.1
    random_state: int = 42
    cv_folds: int = 5
    healthy_quantile: float = 0.75


def _healthy_mask(df: pd.DataFrame, q: float) -> pd.Series:
    """A block group is 'healthy' when its hygiene signal is clean.

    Prefer real violation signal when available (critical_rate below city
    median, failure_rate below city median, at least one inspection in the
    last 24 months). Fall back to the density-proxy for BGs we have no
    inspection data on.
    """
    has_viol = (df["inspections_24mo"] > 0) & df["critical_rate"].notna()
    if has_viol.sum() > 50:
        crit_med = df.loc[has_viol, "critical_rate"].median()
        fail_med = df.loc[has_viol, "failure_rate"].median()
        healthy = (
            (df["critical_rate"] <= crit_med)
            & (df["failure_rate"] <= fail_med)
            & (df["inspections_24mo"] > 0)
            & (df[TARGET] > 0)
        )
        return healthy

    thresh = df[TARGET].quantile(q)
    return df[TARGET].between(0.01, thresh)


def train(hp: HyperParams | None = None):
    hp = hp or HyperParams()
    df = pd.read_parquet(DATA_PROCESSED / "features.parquet").dropna(subset=FEATURES + [TARGET])
    df = df[df["total_pop"] > 100]

    mask = _healthy_mask(df, hp.healthy_quantile)
    train_df = df[mask].copy()
    X, y = train_df[FEATURES], train_df[TARGET]

    model = lgb.LGBMRegressor(
        n_estimators=hp.n_estimators,
        learning_rate=hp.learning_rate,
        num_leaves=hp.num_leaves,
        min_child_samples=hp.min_child_samples,
        reg_lambda=hp.reg_lambda,
        random_state=hp.random_state,
        verbose=-1,
    )
    kf = KFold(n_splits=hp.cv_folds, shuffle=True, random_state=hp.random_state)
    cv_pred = cross_val_predict(model, X, y, cv=kf)
    residual_sigma = float(np.std(y - cv_pred))

    model.fit(X, y)

    df["recommended_per_1000"] = model.predict(df[FEATURES])
    df["recommended_mid"] = df["recommended_per_1000"] * df["total_pop"] / 1000
    df["recommended_min"] = np.clip(
        (df["recommended_per_1000"] - residual_sigma) * df["total_pop"] / 1000, 0, None
    )
    df["recommended_max"] = (df["recommended_per_1000"] + residual_sigma) * df["total_pop"] / 1000
    df["saturation_index"] = df["restaurant_count"] / df["recommended_mid"].replace(0, np.nan)
    df["risk_flag"] = np.where(
        df["saturation_index"] > 1.1, "oversaturated",
        np.where(df["saturation_index"] < 0.5, "underserved", "balanced"),
    )

    out_pred = DATA_PROCESSED / "predictions.parquet"
    df.to_parquet(out_pred)

    model_path = DATA_PROCESSED / "capacity_model.joblib"
    joblib.dump({"model": model, "features": FEATURES, "sigma": residual_sigma}, model_path)
    (DATA_PROCESSED / "hyperparams.json").write_text(json.dumps(asdict(hp), indent=2))

    print(f"trained on {mask.sum()} healthy BGs, σ={residual_sigma:.3f}")
    print(f"wrote predictions → {out_pred}")
    print(f"wrote model → {model_path}")
    return df


if __name__ == "__main__":
    train()
