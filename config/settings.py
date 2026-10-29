from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_RAW.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

CENSUS_API_KEY = os.getenv("CENSUS_API_KEY", "")

BOSTON_STATE_FIPS = "25"
SUFFOLK_COUNTY_FIPS = "025"

ACS_YEAR = 2022
ACS_DATASET = "acs/acs5"

BOSTON_FOOD_INSPECTIONS_RESOURCE = "4582bec6-2b4f-4f9e-bc55-cbaa73117f4c"
BOSTON_OPEN_DATA_BASE = "https://data.boston.gov/api/3/action/datastore_search"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

BOSTON_BBOX = (42.2279, -71.1912, 42.3970, -70.9230)
