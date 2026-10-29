"""LEHD LODES Workplace Area Characteristics (WAC) — jobs by work census block.

Download the WAC file for MA, filter to Suffolk County, roll up block → block group.
This gives us 'daytime population' (where people work), which is a huge demand
driver for restaurants (downtown, Longwood, Seaport).

LODES docs: https://lehd.ces.census.gov/data/lodes/LODES8/
File pattern: ma_wac_S000_JT00_{year}.csv.gz   (S000 = all workers, JT00 = all jobs)
"""
from __future__ import annotations
import io
import gzip
import requests
import pandas as pd
from config.settings import DATA_RAW, BOSTON_STATE_FIPS, SUFFOLK_COUNTY_FIPS

LODES_YEAR = 2021
LODES_URL = (
    f"https://lehd.ces.census.gov/data/lodes/LODES8/ma/wac/"
    f"ma_wac_S000_JT00_{LODES_YEAR}.csv.gz"
)


def fetch_lodes_wac() -> pd.DataFrame:
    print(f"downloading LODES WAC {LODES_YEAR} …")
    r = requests.get(LODES_URL, timeout=180)
    r.raise_for_status()
    df = pd.read_csv(io.BytesIO(gzip.decompress(r.content)), dtype={"w_geocode": str})

    county_prefix = BOSTON_STATE_FIPS + SUFFOLK_COUNTY_FIPS
    df = df[df["w_geocode"].str.startswith(county_prefix)].copy()
    df["geoid"] = df["w_geocode"].str[:12]

    agg = df.groupby("geoid").agg(
        jobs_total=("C000", "sum"),
        jobs_food_accom=("CNS18", "sum"),
        jobs_retail=("CNS07", "sum"),
        jobs_high_wage=("CE03", "sum"),
    ).reset_index()

    out = DATA_RAW / "lodes_wac_by_bg.parquet"
    agg.to_parquet(out)
    print(f"wrote LODES jobs for {len(agg)} BGs → {out}")
    return agg


if __name__ == "__main__":
    fetch_lodes_wac()
