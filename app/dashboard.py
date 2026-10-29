# ============================================================================
#                                   ___
#                                __/   \__       ~  JAI  SHARMA  ~
#                           ___ /    _    \ ___
#                          /   V   _( )_   V   \       DASHBOARD DRAGON
#                         |  (o)  /  ~  \  (o)  |
#                          \     / BOSTON \     /     ~ breathing charts ~
#                           '---/          \---'
#                              /  SATURATION \
#                             /________________\         .-'''-.
#                             |||            |||       .'       '.
#                             |||  Jai Shrm  |||      /  ))))     \
#                             '-'            '-'      \___________/
# ============================================================================
"""Streamlit dashboard for the Boston restaurant saturation model."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import st_folium
from config.settings import DATA_PROCESSED, DATA_RAW

st.set_page_config(page_title="Boston Restaurant Saturation", layout="wide", page_icon="🍽️")

st.markdown("""
<style>
  .big-metric {font-size: 2.2rem; font-weight: 700;}
  .sub {color: #888; font-size: .9rem;}
  div[data-testid="stMetricValue"] {font-size: 1.6rem;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_preds():
    return pd.read_parquet(DATA_PROCESSED / "predictions.parquet")

@st.cache_data
def load_cuisines():
    p = DATA_PROCESSED / "cuisine_recs.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()

@st.cache_data
def load_bg_geom():
    from src.features.build import _load_blockgroups_gdf
    return _load_blockgroups_gdf()

try:
    df = load_preds()
except FileNotFoundError:
    st.error("Run `python -m src.pipeline all` first to generate predictions.")
    st.stop()

cuisines = load_cuisines()

st.title("🍽️ Boston Restaurant Saturation")
st.caption("How many restaurants should each block group carry — and which cuisines are underserved?  ·  ~ built by JAI SHARMA ~")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Block groups", f"{len(df):,}")
col2.metric("Total restaurants", f"{int(df['restaurant_count'].sum()):,}")
col3.metric("Oversaturated BGs", f"{(df['risk_flag']=='oversaturated').sum():,}")
col4.metric("Underserved BGs", f"{(df['risk_flag']=='underserved').sum():,}")

st.sidebar.header("Filters")
min_pop = st.sidebar.slider("Min population", 0, 5000, 200, 100)
risk = st.sidebar.multiselect(
    "Risk flag", ["balanced", "oversaturated", "underserved"],
    default=["balanced", "oversaturated", "underserved"],
)
view = df[(df["total_pop"] >= min_pop) & (df["risk_flag"].isin(risk))].copy()

tab_map, tab_table, tab_chart, tab_cuisine, tab_whatif = st.tabs(
    ["🗺️ Map", "📋 Table", "📊 Distribution", "🥘 Cuisine recs", "🧪 What-if"]
)

with tab_map:
    bg_geom = load_bg_geom()
    merged = bg_geom.merge(view, on="geoid", how="inner")
    if merged.empty:
        st.info("No block groups match filters.")
    else:
        m = folium.Map(location=[42.3200, -71.07], zoom_start=12, tiles="cartodbpositron")
        folium.Choropleth(
            geo_data=json.loads(merged.to_json()),
            data=merged,
            columns=["geoid", "saturation_index"],
            key_on="feature.properties.geoid",
            fill_color="RdYlGn_r",
            fill_opacity=0.75,
            line_opacity=0.3,
            legend_name="Saturation index (red = oversaturated)",
            nan_fill_color="#eee",
        ).add_to(m)
        for _, row in merged.iterrows():
            folium.CircleMarker(
                [row.geometry.centroid.y, row.geometry.centroid.x],
                radius=3, color="#333", fill=True, fill_opacity=0.6,
                popup=(
                    f"<b>GEOID {row.geoid}</b><br>"
                    f"Pop: {int(row.total_pop or 0):,}<br>"
                    f"Actual: {int(row.restaurant_count)} restaurants<br>"
                    f"Recommended: {row.recommended_min:.0f}–{row.recommended_max:.0f}<br>"
                    f"Saturation: {row.saturation_index:.2f} ({row.risk_flag})"
                ),
            ).add_to(m)
        st_folium(m, height=600, use_container_width=True)

with tab_table:
    cols = [
        "geoid", "total_pop", "pop_density", "median_income",
        "restaurant_count", "recommended_min", "recommended_max",
        "saturation_index", "risk_flag",
    ]
    st.dataframe(
        view[cols].sort_values("saturation_index", ascending=False),
        use_container_width=True, hide_index=True,
    )
    st.download_button(
        "Download CSV", view[cols].to_csv(index=False).encode(),
        "boston_saturation.csv", "text/csv",
    )

with tab_chart:
    c1, c2 = st.columns(2)
    with c1:
        fig = px.histogram(view, x="saturation_index", nbins=40,
                           title="Saturation index distribution",
                           color="risk_flag",
                           color_discrete_map={
                               "balanced": "#4caf50",
                               "oversaturated": "#e53935",
                               "underserved": "#fb8c00",
                           })
        fig.add_vline(x=1.0, line_dash="dash")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig2 = px.scatter(
            view, x="pop_density", y="restaurant_count",
            size="total_pop", color="saturation_index",
            color_continuous_scale="RdYlGn_r",
            hover_data=["geoid", "median_income"],
            title="Density vs. restaurant count (bubble = population)",
        )
        st.plotly_chart(fig2, use_container_width=True)

with tab_cuisine:
    if cuisines.empty:
        st.info("Cuisine recommendations not generated yet.")
    else:
        geoid_pick = st.selectbox("Pick a block group", view["geoid"].tolist())
        row = cuisines[cuisines["geoid"] == geoid_pick]
        if row.empty:
            st.warning("No cuisine data for this block group.")
        else:
            rec = row.iloc[0]["recommended_cuisines"]
            target = row.iloc[0]["target_mix"]
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Most underserved cuisines")
                st.dataframe(pd.Series(rec).rename("gap").reset_index().rename(columns={"index":"cuisine"}))
            with c2:
                st.subheader("Peer target mix (healthy BGs)")
                st.dataframe(pd.Series(target).rename("share").reset_index().rename(columns={"index":"cuisine"}))

with tab_whatif:
    st.subheader("Drop a pin → predict survival + saturation shift")
    st.caption("Pick a location and (optional) cuisine. The model returns the 24-month survival probability, "
               "how much your opening pushes local saturation, and nearby restaurants that would be cannibalized.")
    c1, c2, c3 = st.columns(3)
    with c1:
        lat = st.number_input("Latitude", value=42.3200, format="%.5f")
    with c2:
        lon = st.number_input("Longitude", value=-71.0700, format="%.5f")
    with c3:
        if not cuisines.empty and "target_mix" in cuisines.columns:
            all_cuis = sorted({k for r in cuisines["target_mix"].tolist() for k in (r or {})})
        else:
            all_cuis = []
        cuisine_choice = st.selectbox("Cuisine (optional)", [""] + all_cuis)

    if st.button("Run what-if", type="primary"):
        try:
            import requests
            r = requests.post("http://127.0.0.1:8000/whatif", json={
                "lat": lat, "lon": lon,
                "cuisine": cuisine_choice or None,
                "cannibalization_radius_m": 500,
            }, timeout=10)
            if r.status_code == 200:
                out = r.json()
                v = out["verdict"]
                color = {"go": "#2e7d32", "risky": "#f9a825", "avoid": "#c62828"}[v]
                st.markdown(
                    f"<div style='padding:14px;border-radius:8px;background:{color};color:white;"
                    f"font-size:1.4rem;font-weight:600'>Verdict: {v.upper()}</div>",
                    unsafe_allow_html=True,
                )
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Survival (24 mo)", f"{out['survival_probability']*100:.1f}%")
                m2.metric("Saturation Δ", f"{out['saturation_before']:.2f} → {out['saturation_after']:.2f}")
                m3.metric("Cuisine fit", f"{out['cuisine_fit']:.2f}")
                m4.metric("Cannibalized (500 m)", out["cannibalized_restaurants"])
                st.caption(f"Nearest block group: {out['geoid']}")
            else:
                st.error(f"API error {r.status_code}: {r.text}")
        except Exception as e:
            st.warning(f"Could not reach API — start it with `uvicorn app.api:app --port 8000`. ({e})")
