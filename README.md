# 🍽️ Boston Restaurant Saturation Model

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009485.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/UI-Next.js%2014-black.svg)](https://nextjs.org/)
[![LightGBM](https://img.shields.io/badge/ML-LightGBM-21A366.svg)](https://lightgbm.readthedocs.io/)

> **How many restaurants should each Boston block group carry — and which cuisines are underserved?**
> A full pipeline (scrape → feature → model → API → dashboard) that answers the question for every one of Boston's 681 census block groups.

A restaurant market has a **carrying capacity**. Overshoot it and you get thinner margins → lower hygiene investment → inspection failures, higher turnover, trash/pest issues, and cannibalized revenue for incumbents. This project models that capacity and tells you where new restaurants will probably thrive — or die.

---

## ✨ What it does

For every census block group in Boston, this project outputs:

- **`recommended_min` / `recommended_max`** — healthy restaurant count band
- **`saturation_index`** — 0 = empty market, 1 = saturated, >1 = oversaturated
- **`cuisine_mix`** — ranked list of underserved cuisines based on demographic fit
- **`survival_probability`** — 24-month survival chance for a new restaurant here
- **`risk_flag`** — balanced / oversaturated / underserved

And an interactive **"what-if simulator"**: drop a pin, pick a cuisine, get a GO / RISKY / AVOID verdict with survival probability and cannibalization count.

---

## 🏗 Architecture

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌───────────────┐
│  Scrapers    │ → │  Features    │ → │  Models      │ → │  API + UIs    │
├──────────────┤   ├──────────────┤   ├──────────────┤   ├───────────────┤
│ Census ACS   │   │ pop density  │   │ Capacity     │   │ FastAPI       │
│ OSM          │   │ daytime pop  │   │  (LightGBM)  │   │ Streamlit     │
│ data.boston  │   │ cuisine div. │   │ Cuisine kNN  │   │ Next.js 14    │
│ LEHD LODES   │   │ hygiene risk │   │ Survival clf │   │ (Tailwind +   │
│ Yelp (opt.)  │   │              │   │              │   │  MapLibre)    │
└──────────────┘   └──────────────┘   └──────────────┘   └───────────────┘
```

Three stacked models:

1. **Capacity regressor** (LightGBM) — trained only on *healthy* block groups (low hygiene violation rate) to learn the carrying-capacity surface. ±1σ residuals give the recommended min/max band.
2. **Cuisine recommender** (kNN over demographics) — finds k nearest healthy BGs in demographic space, averages their cuisine distribution, subtracts the local actual mix → underserved cuisines.
3. **Survival classifier** (LightGBM) — reconstructs business lifespans from inspection first/last dates, predicts P(a new restaurant here survives 24 months).

---

## 📸 Screenshots

![Dashboard](docs/dashboard.png)
![What-if simulator](docs/whatif.png)

*(Screenshots live in `docs/`. Replace with your own after running once.)*

---

## 🚀 Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+ (only for the Next.js UI)
- `libomp` on macOS: `brew install libomp` (LightGBM needs it)
- A **free US Census API key** — https://api.census.gov/data/key_signup.html

### 1 — Install

```bash
git clone https://github.com/jai0812/boston-restaurant-saturation.git
cd boston-restaurant-saturation
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then paste your Census key into CENSUS_API_KEY
```

### 2 — Run the pipeline

```bash
python -m src.pipeline fetch       # Census + OSM + Boston inspections + LODES (~5–8 min)
python -m src.pipeline features    # join + build feature table
python -m src.pipeline train       # train capacity + cuisine + survival models
```

### 3 — Launch a dashboard

**Option A: Streamlit (fast)**
```bash
PYTHONPATH=. streamlit run app/dashboard.py
```

**Option B: FastAPI + Next.js (polished)**
```bash
uvicorn app.api:app --port 8000 --reload       # terminal 1
cd web && npm install && npm run dev           # terminal 2
# open http://localhost:3000
```

---

## 📂 Project layout

```
.
├── config/settings.py           # API keys, paths, constants
├── data/
│   ├── raw/                     # untouched API dumps (parquet)
│   └── processed/               # feature table + predictions
├── src/
│   ├── scrapers/
│   │   ├── census_api.py        # ACS demographics
│   │   ├── osm_restaurants.py   # OSM Overpass restaurant POIs
│   │   ├── boston_data.py       # Boston food-inspection history
│   │   ├── lodes.py             # LEHD LODES workplace jobs
│   │   └── yelp_scraper.py      # Selenium fallback for Yelp
│   ├── features/
│   │   ├── build.py             # geocoding + per-BG aggregation
│   │   └── violations.py        # hygiene risk per block group
│   ├── model/
│   │   ├── capacity_model.py    # LightGBM carrying-capacity regressor
│   │   ├── cuisine_recommender.py
│   │   └── survival_model.py    # 24-month survival classifier
│   └── pipeline.py              # CLI entrypoint
├── app/
│   ├── api.py                   # FastAPI service
│   └── dashboard.py             # Streamlit dashboard
├── web/                         # Next.js 14 + Tailwind + MapLibre + Recharts
├── requirements.txt
└── README.md
```

---

## 🔌 API

Once `uvicorn app.api:app` is running on port 8000:

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness check |
| `GET /stats` | City-wide totals |
| `GET /blockgroups?risk=oversaturated&limit=500` | List BGs by filter |
| `GET /blockgroup/{geoid}` | Full detail for one BG, incl. cuisine recs |
| `POST /whatif` | Simulate opening a new restaurant: body `{lat, lon, cuisine?, cannibalization_radius_m?}` |

Example:
```bash
curl -X POST http://127.0.0.1:8000/whatif \
  -H 'Content-Type: application/json' \
  -d '{"lat":42.3550,"lon":-71.0656,"cuisine":"vietnamese"}'
```

---

## 🧮 Data sources

| Source | Why | Access |
|---|---|---|
| [US Census ACS 5-year](https://www.census.gov/data/developers/data-sets/acs-5year.html) | Population, age, income, race, student share, household size | Free API key |
| [OpenStreetMap Overpass](https://wiki.openstreetmap.org/wiki/Overpass_API) | Restaurant POIs + cuisine tags | Free, no key |
| [Analyze Boston — Food Establishment Inspections](https://data.boston.gov/dataset/food-establishment-inspections) | Hygiene violations, business lifecycle | Free CKAN API, no key |
| [LEHD LODES WAC](https://lehd.ces.census.gov/data/) | Daytime population (jobs by workplace) | Free, no key |
| [TIGER/Line](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html) | Block-group polygons | Free, no key |

---

## 🧭 Roadmap

- [x] Capacity, cuisine, and survival models
- [x] FastAPI service
- [x] Streamlit dashboard with what-if simulator
- [x] Next.js dashboard with MapLibre + Recharts
- [ ] LLM narrative layer (plain-English BG explanations)
- [ ] Lease-price integration (LoopNet scrape)
- [ ] MBTA walkability + isochrones
- [ ] Multi-city (NYC, SF, Chicago)
- [ ] Dockerfile + Vercel/Railway deploy
- [ ] SHAP feature-importance page
- [ ] Pytest + GitHub Actions CI

PRs welcome — see the issues tab for first-good-issue tagged items.

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

## 🙏 Credits

Built by **[Jai Sharma](https://github.com/jai0812)**.

Data courtesy of the US Census Bureau, City of Boston, OpenStreetMap contributors,
and the LEHD program.

```
                                                 J       A
                    IS                           HA     RM
                  AJAISH                         ARMAJAISHAR
                MAJAISHARM                      AJAI00SHARMAJAI
              SHARMAJAISHARM                   AJAISHARMAJAISHARMAJ
            AISHARMAJAISHARMAJ                AISHARMAJAISHARMAJAISHAR
          MAJAISHARMAJAISHARMAJA             ISHARMAJAISHARMA  JA  IS H
        ARMAJAISHARMAJAISHARMAJAIS          HARMAJAISHAR   MA  JA
      ISHARMAJAISHARMAJAISHARMAJAISH       ARMAJAISHAR
          MAJAISHARMAJAISHARMAJAISHARM    AJAISHARMA
 J           AISHARMAJAISHARMAJAISHARMAJAISHARM
 AJ        AISHARMAJAISHARMAJAISHARMAJAISHARMA
 JAI     SHARMAJAISHARMAJAISHARMAJAISHARMAJA
  ISHA  RMAJAISHARMAJAISHARMAJAISHARMAJAISH
   ARMAJAISHARMAJAISHARMAJAISHARMAJAISHAR
     MAJAISHARMAJAISHARMAJAISHARMAJAISH
        ARMAJAISHAR  MAJAISHA   RMAJAISH

            ~ built by JAI SHARMA ~
```
