"""US Census ACS 5-year pull for Suffolk County (Boston) block groups.

Variables (ACS 2022):
  B01003_001E  total population
  B01002_001E  median age
  B19013_001E  median household income
  B14001_008E  enrolled in college/grad school (students)
  B02001_002E  White alone
  B02001_003E  Black alone
  B02001_005E  Asian alone
  B03003_003E  Hispanic/Latino
  B11001_001E  total households
  B25010_001E  avg household size
"""
from __future__ import annotations
import json
import requests
import pandas as pd
from config.settings import (
    CENSUS_API_KEY, ACS_YEAR, ACS_DATASET,
    BOSTON_STATE_FIPS, SUFFOLK_COUNTY_FIPS, DATA_RAW,
)

VARIABLES = {
    "B01003_001E": "total_pop",
    "B01002_001E": "median_age",
    "B19013_001E": "median_income",
    "B14001_008E": "college_students",
    "B02001_002E": "white",
    "B02001_003E": "black",
    "B02001_005E": "asian",
    "B03003_003E": "hispanic",
    "B11001_001E": "households",
    "B25010_001E": "avg_hh_size",
}


def fetch_acs_blockgroups() -> pd.DataFrame:
    url = f"https://api.census.gov/data/{ACS_YEAR}/{ACS_DATASET}"
    params = {
        "get": ",".join(VARIABLES.keys()) + ",NAME",
        "for": "block group:*",
        "in": f"state:{BOSTON_STATE_FIPS} county:{SUFFOLK_COUNTY_FIPS}",
    }
    if CENSUS_API_KEY:
        params["key"] = CENSUS_API_KEY

    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    rows = r.json()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df = df.rename(columns=VARIABLES)

    for col in VARIABLES.values():
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["geoid"] = (
        df["state"] + df["county"] + df["tract"] + df["block group"]
    )
    df["pct_students"] = df["college_students"] / df["total_pop"].replace(0, pd.NA)
    df["pct_white"] = df["white"] / df["total_pop"].replace(0, pd.NA)
    df["pct_black"] = df["black"] / df["total_pop"].replace(0, pd.NA)
    df["pct_asian"] = df["asian"] / df["total_pop"].replace(0, pd.NA)
    df["pct_hispanic"] = df["hispanic"] / df["total_pop"].replace(0, pd.NA)

    out = DATA_RAW / "census_acs_blockgroups.parquet"
    df.to_parquet(out)
    print(f"wrote {len(df)} block groups → {out}")
    return df


if __name__ == "__main__":
    fetch_acs_blockgroups()
