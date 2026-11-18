# Global Climate Trends — Interactive Dashboard

A multi-page Dash app exploring four questions about CO2 emissions, warming,
and the energy transition:

1. Has global CO2 growth slowed since 2000?
2. Who emits most in total, versus per person?
3. Does higher GDP still mean higher emissions per person?
4. Is renewable electricity adoption tracking natural solar/wind potential?

Each question has its own page (`/q1`, `/q2`, `/q3`, `/q4`), plus an
overview page (`/`) with headline numbers, and three supplementary pages: a
per-country drill-down (`/country`), a two-year comparison view
(`/compare`), and an AI Footprint page (`/ai-footprint`) estimating the
water/energy/carbon cost of an AI prompt against the same per-country data.

## Data sources

- **Our World in Data**, [CO2 and Greenhouse Gas Emissions](https://github.com/owid/co2-data) (CC BY 4.0)
- **Our World in Data**, [Energy](https://github.com/owid/energy-data) (CC BY 4.0)
- **NASA GISS**, [GISTEMP v4](https://data.giss.nasa.gov/gistemp/) global land-ocean temperature index (public domain)
- **NASA POWER**, [solar/wind climatology](https://power.larc.nasa.gov/) — fetched once per country capital and cached in `data/power_climatology.csv`; the running app makes no calls to this API (public domain)
- **AI Footprint reference table** (`data/ai_footprint.csv`) — modeled, not measured: derived from [MIT News, "Explained: Generative AI's environmental impact"](https://news.mit.edu/2025/explained-generative-ai-environmental-impact-0117) (Jan 2025) and cross-checked for plausible order of magnitude against the [ClimateAligned AI Footprint Calculator](https://www.climatealigned.co/tools/ai-footprint-calculator)'s methodology

## Files

| File | Purpose |
|---|---|
| `data/__init__.py` | `LoadedData` dataclass + `load_all()` — loads every source once at startup |
| `data/co2.py` | OWID CO2 loading and the cleaning rules documented in `CLAUDE.md` |
| `data/gistemp.py` | GISTEMP loading, including its preamble/asterisk parsing quirks |
| `data/energy.py` | OWID Energy loading and the renewable-share column choice |
| `data/climatology.py` | Reads the committed NASA POWER climatology cache |
| `data/ai_footprint.py` | Loads the curated AI-model footprint reference table |
| `data/ai_footprint.csv` | Curated per-model, per-use-case energy/carbon/water reference table (modeled, not measured — see Data sources) |
| `data/capitals.csv` | One capital city lat/lon per country (218 rows) — input to the cache-building script |
| `data/power_climatology.csv` | Committed NASA POWER solar/wind climatology cache |
| `scripts/build_climatology_cache.py` | One-time, offline script that (re)builds `data/power_climatology.csv`. Only needed if that cache file needs regenerating — a normal `pip install && python app.py` does not run it, since the cache is already committed |
| `profile_dataset.py` | Reproduces the dataset profile behind the cleaning rules |
| `prototype_charts.py` | The Q1-Q3 chart functions |
| `q4_charts.py` | The Q4 chart function (renewable adoption vs solar/wind potential) |
| `country_profile_charts.py` | Country Climate Profile: trend-sparkline chart builder |
| `ai_footprint_charts.py` | AI Footprint page charts: per-model comparison and per-capita context |
| `analysis.py` | Pure numeric helpers: Q1 trend helpers, plus generic country-series/year-comparison helpers used by the Country Profile and Compare Years pages |
| `ai_footprint_analysis.py` | Pure numeric helpers for the AI Footprint page: prompt-length bucketing and per-capita share calculation |
| `state.py` | Calls `data.load_all()` once at import time; every page reads `state.loaded` |
| `app.py` | The Dash app shell: nav, footer, and the `use_pages=True` page container |
| `pages/overview.py` | Landing page (`/`) |
| `pages/q1_growth.py` | Q1 page (`/q1`) |
| `pages/q2_emitters.py` | Q2 page (`/q2`), with a CSV download button |
| `pages/q3_gdp.py` | Q3 page (`/q3`), with a CSV download button |
| `pages/q4_renewables.py` | Q4 page (`/q4`), with a CSV download button |
| `pages/country_profile.py` | Country Profile page (`/country`): country picker, KPI cards, 1990-present trend sparklines |
| `pages/compare_years.py` | Compare Years page (`/compare`): pick two years, see global CO2 / CO2-per-person / renewables / temperature deltas |
| `pages/ai_footprint.py` | AI Footprint page (`/ai-footprint`): model/use-case/frequency controls, free-text prompt override, per-capita comparison, CSV download |
| `tests/` | 51 unit tests for the cleaning rules, analysis helpers, capitals reference, cache-building, chart helpers, and the AI footprint reference-table/analysis helpers |

## Running locally

```bash
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:8050/.

This does **not** require running `scripts/build_climatology_cache.py` —
`data/power_climatology.csv` is already committed. Only regenerate it (by
running that script) if the cache needs to be rebuilt, e.g. after adding a
country to `data/capitals.csv`.

## Tests

```bash
pip install pytest
pytest tests/
```

## Deploying to Render (free tier)

1. Push this repo to GitHub.
2. On Render: New → Web Service → connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:server` (also in `Procfile`)
5. No environment variables or API keys are required — the live data sources are public CSVs fetched at startup, and the NASA POWER climatology is read from the committed cache file, not fetched live.
