"""Generate publication-quality charts for the README documentation.

Writes PNGs into docs/ at a resolution that looks crisp on GitHub.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import pandas as pd
import joblib

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config.settings import DATA_PROCESSED

DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)

mpl.rcParams.update({
    "figure.dpi": 140,
    "savefig.dpi": 140,
    "savefig.bbox": "tight",
    "savefig.facecolor": "#0a0b0f",
    "axes.facecolor": "#0a0b0f",
    "figure.facecolor": "#0a0b0f",
    "axes.edgecolor": "#3a3f52",
    "axes.labelcolor": "#e8eaf0",
    "xtick.color": "#8b90a3",
    "ytick.color": "#8b90a3",
    "text.color": "#e8eaf0",
    "axes.titlecolor": "#e8eaf0",
    "axes.titleweight": "bold",
    "axes.titlesize": 14,
    "axes.labelweight": "600",
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "grid.color": "#232634",
    "grid.alpha": 0.6,
})

ACCENT = "#ff6b35"
GOOD = "#4ade80"
WARN = "#f59e0b"
BAD = "#ef4444"

preds = pd.read_parquet(DATA_PROCESSED / "predictions.parquet")


def chart_1_saturation_distribution():
    fig, ax = plt.subplots(figsize=(10, 5))
    sat = preds["saturation_index"].dropna()
    sat = sat.clip(-5, 10)
    bins = np.linspace(-5, 10, 50)
    for flag, color in [("underserved", GOOD), ("balanced", WARN), ("oversaturated", BAD)]:
        subset = preds.loc[preds["risk_flag"] == flag, "saturation_index"].dropna().clip(-5, 10)
        ax.hist(subset, bins=bins, color=color, alpha=0.75, edgecolor="#0a0b0f",
                linewidth=0.6, label=f"{flag} ({len(subset)})")
    ax.axvline(1.0, color=ACCENT, linestyle="--", linewidth=1.6, alpha=0.9, label="saturation = 1.0")
    ax.set_title("Boston block-group saturation index — 680 block groups", loc="left")
    ax.set_xlabel("saturation = actual restaurants / recommended capacity")
    ax.set_ylabel("count of block groups")
    ax.grid(axis="y", linestyle=":")
    ax.legend(frameon=False, loc="upper right")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.savefig(DOCS / "saturation_distribution.png")
    plt.close(fig)
    print("wrote docs/saturation_distribution.png")


def chart_2_feature_importance():
    bundle = joblib.load(DATA_PROCESSED / "capacity_model.joblib")
    model, feats = bundle["model"], bundle["features"]
    importances = pd.Series(model.feature_importances_, index=feats).sort_values()

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = plt.get_cmap("plasma")(np.linspace(0.15, 0.85, len(importances)))
    ax.barh(importances.index, importances.values, color=colors, edgecolor="#0a0b0f")
    ax.set_title("Capacity-model feature importance (LightGBM gain)", loc="left")
    ax.set_xlabel("relative importance")
    ax.grid(axis="x", linestyle=":")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.savefig(DOCS / "feature_importance.png")
    plt.close(fig)
    print("wrote docs/feature_importance.png")


def chart_3_density_vs_restaurants():
    fig, ax = plt.subplots(figsize=(10, 6))
    df = preds.dropna(subset=["pop_density", "restaurant_count", "saturation_index"]).copy()
    df["sat_clipped"] = df["saturation_index"].clip(-5, 5)
    sc = ax.scatter(
        df["pop_density"] / 1000,
        df["restaurant_count"],
        c=df["sat_clipped"],
        cmap="RdYlGn_r",
        s=np.clip(df["total_pop"].fillna(500) / 50, 10, 300),
        alpha=0.75,
        edgecolor="#13151c",
        linewidth=0.5,
    )
    cbar = fig.colorbar(sc, ax=ax, pad=0.02)
    cbar.set_label("saturation index", color="#e8eaf0")
    cbar.ax.yaxis.set_tick_params(color="#8b90a3")
    plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color="#e8eaf0")
    ax.set_xscale("symlog")
    ax.set_yscale("symlog")
    ax.set_title("Population density vs. restaurant count (bubble = population)", loc="left")
    ax.set_xlabel("population density (thousand people / km²)")
    ax.set_ylabel("restaurant count per block group")
    ax.grid(linestyle=":")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.savefig(DOCS / "density_vs_restaurants.png")
    plt.close(fig)
    print("wrote docs/density_vs_restaurants.png")


def chart_4_cuisine_mix():
    osm = pd.read_parquet(ROOT / "data/raw/osm_restaurants.parquet")
    top = osm["cuisine"].dropna().str.split(";").str[0].value_counts().head(15)

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = plt.get_cmap("viridis")(np.linspace(0.2, 0.9, len(top)))
    ax.barh(top.index[::-1], top.values[::-1], color=colors, edgecolor="#0a0b0f")
    ax.set_title("Top 15 restaurant cuisines in Boston (OpenStreetMap tags)", loc="left")
    ax.set_xlabel("restaurant count")
    ax.grid(axis="x", linestyle=":")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.savefig(DOCS / "cuisine_mix.png")
    plt.close(fig)
    print("wrote docs/cuisine_mix.png")


def chart_5_risk_breakdown():
    counts = preds["risk_flag"].value_counts()
    colors = {"balanced": WARN, "oversaturated": BAD, "underserved": GOOD}
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(counts.index, counts.values,
                  color=[colors[c] for c in counts.index], edgecolor="#0a0b0f", linewidth=1.5)
    for b, v in zip(bars, counts.values):
        ax.text(b.get_x() + b.get_width()/2, v + 5, str(v),
                ha="center", va="bottom", fontweight="bold", fontsize=12)
    ax.set_title("Risk-flag breakdown across 680 Boston block groups", loc="left")
    ax.set_ylabel("count of block groups")
    ax.grid(axis="y", linestyle=":")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.savefig(DOCS / "risk_breakdown.png")
    plt.close(fig)
    print("wrote docs/risk_breakdown.png")


if __name__ == "__main__":
    chart_1_saturation_distribution()
    chart_2_feature_importance()
    chart_3_density_vs_restaurants()
    chart_4_cuisine_mix()
    chart_5_risk_breakdown()
    print("done →", DOCS)
