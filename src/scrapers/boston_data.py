"""Pull Boston food establishment inspections from data.boston.gov CKAN API.

Each row includes business name, address, lat/lon, license category, and
violation details. We paginate through the datastore endpoint.
"""
from __future__ import annotations
import requests
import pandas as pd
from tqdm import tqdm
from config.settings import BOSTON_OPEN_DATA_BASE, BOSTON_FOOD_INSPECTIONS_RESOURCE, DATA_RAW

PAGE_SIZE = 10_000


def fetch_inspections(limit: int | None = None) -> pd.DataFrame:
    offset = 0
    frames = []
    pbar = tqdm(desc="inspections", unit="rows")
    while True:
        params = {
            "resource_id": BOSTON_FOOD_INSPECTIONS_RESOURCE,
            "limit": PAGE_SIZE,
            "offset": offset,
        }
        r = requests.get(BOSTON_OPEN_DATA_BASE, params=params, timeout=120)
        r.raise_for_status()
        payload = r.json()["result"]
        records = payload.get("records", [])
        if not records:
            break
        frames.append(pd.DataFrame(records))
        pbar.update(len(records))
        offset += len(records)
        if limit and offset >= limit:
            break
        if len(records) < PAGE_SIZE:
            break
    pbar.close()

    df = pd.concat(frames, ignore_index=True)
    out = DATA_RAW / "boston_food_inspections.parquet"
    df.to_parquet(out)
    print(f"wrote {len(df):,} inspection records → {out}")
    return df


if __name__ == "__main__":
    fetch_inspections()
