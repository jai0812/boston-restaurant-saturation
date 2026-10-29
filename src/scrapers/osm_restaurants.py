"""Pull restaurant POIs from OpenStreetMap via Overpass API.

Returns a dataframe with lat/lon, name, and cuisine tag for every
amenity=restaurant|cafe|fast_food in Boston's bounding box.
"""
from __future__ import annotations
import requests
import pandas as pd
from config.settings import OVERPASS_URL, BOSTON_BBOX, DATA_RAW

QUERY_TMPL = """
[out:json][timeout:120];
(
  node["amenity"~"restaurant|cafe|fast_food"]({s},{w},{n},{e});
  way["amenity"~"restaurant|cafe|fast_food"]({s},{w},{n},{e});
);
out center tags;
"""


def fetch_osm_restaurants() -> pd.DataFrame:
    s, w, n, e = BOSTON_BBOX
    query = QUERY_TMPL.format(s=s, w=w, n=n, e=e)
    headers = {"User-Agent": "boston-restaurant-saturation/0.1 (research)"}
    r = requests.post(OVERPASS_URL, data={"data": query}, headers=headers, timeout=180)
    r.raise_for_status()
    elements = r.json()["elements"]

    rows = []
    for el in elements:
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None or lon is None:
            continue
        tags = el.get("tags", {})
        rows.append({
            "osm_id": el["id"],
            "lat": lat,
            "lon": lon,
            "name": tags.get("name"),
            "cuisine": tags.get("cuisine"),
            "amenity": tags.get("amenity"),
            "takeaway": tags.get("takeaway"),
        })

    df = pd.DataFrame(rows)
    out = DATA_RAW / "osm_restaurants.parquet"
    df.to_parquet(out)
    print(f"wrote {len(df):,} OSM restaurants → {out}")
    return df


if __name__ == "__main__":
    fetch_osm_restaurants()
