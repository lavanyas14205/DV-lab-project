# Global Climate Trends — Interactive Dashboard

Academic mini-project for a Data Visualization lab. Built with Python, Pandas,
Plotly and Dash; deployed to Render as a public URL.

## Current state

Week 3 complete (dataset selection). Week 4 complete (Dash app). The dashboard
has since been expanded from a single-page, 3-question app into a multi-page,
4-question app: `data.py` split into a `data/` package, a `pages/` folder
added (one module per question plus an overview), and Q4 (renewable adoption
vs solar/wind potential) added on top of the OWID Energy dataset and a
NASA POWER climatology cache. Deployment to Render is next.

| File | Purpose | Status |
|---|---|---|
| `profile_dataset.py` | Reproduces the dataset profile; graded evidence | Done |
| `prototype_charts.py` | Five Q1-Q3 chart functions, verified against real data | Done |
| `q4_charts.py` | Q4 chart: renewable-adoption-vs-potential bubble with trend-residual labelling, plus `outlier_details()` for the Adoption Leaders / Potential Under-Utilisers callouts | Done |
| `analysis.py` | Pure numeric helpers: Q1 trend helpers, plus generic country-series/year-comparison helpers used by the Country Profile and Compare Years pages | Done |
| `ai_footprint_analysis.py` | Pure numeric helpers for the AI Footprint page: prompt-length bucketing and per-capita share calculation | Done |
| `data/__init__.py` | `LoadedData` dataclass + `load_all()`; orchestrates the source-specific modules below | Done |
| `data/co2.py` | OWID CO2 loading + cleaning rules 1-6 (aggregate filter, GDP cap, sparse columns, year default, modelled-temperature label, per-capita population floor) | Done |
| `data/gistemp.py` | GISTEMP loading + the preamble/asterisk parsing quirks | Done |
| `data/energy.py` | OWID Energy loading; renewable-share column choice (rule 7, below) | Done |
| `data/climatology.py` | Reads the committed NASA POWER climatology cache — no network code in the running app | Done |
| `data/ai_footprint.py` | Loads the curated AI-model footprint reference table | Done |
| `data/ai_footprint.csv` | Curated per-model, per-use-case energy/carbon/water reference table (modeled, not measured) | Done |
| `data/capitals.csv` | Static reference: one capital city lat/lon per country (218 rows); input to the cache-building script | Done |
| `data/power_climatology.csv` | Committed NASA POWER solar/wind climatology cache, keyed by `iso_code` | Done |
| `scripts/build_climatology_cache.py` | One-time, offline script that builds `data/power_climatology.csv` from `data/capitals.csv`; never run by the deployed app | Done |
| `state.py` | Calls `data.load_all()` once at import time; every page reads `state.loaded` | Done |
| `app.py` | Dash app shell: nav, footer, `use_pages=True` page container | Done |
| `pages/overview.py` | Landing page (`/`): all four questions plus headline numbers | Done |
| `pages/q1_growth.py` | Q1 page (`/q1`): dual-axis line + growth-rate bar, year slider | Done |
| `pages/q2_emitters.py` | Q2 page (`/q2`): choropleth + paired bar, year/country/metric controls, CSV download | Done |
| `pages/q3_gdp.py` | Q3 page (`/q3`): GDP-vs-emissions bubble, year/country controls, CSV download | Done |
| `pages/q4_renewables.py` | Q4 page (`/q4`): renewable-potential-vs-adoption bubble, year/potential controls, CSV download | Done |
| `country_profile_charts.py` | Country Climate Profile: trend-sparkline chart builder | Done |
| `ai_footprint_charts.py` | AI Footprint page charts: per-model comparison and per-capita context | Done |
| `pages/country_profile.py` | Country Profile page (`/country`): country picker, KPI cards, 1990-present trend sparklines | Done |
| `pages/compare_years.py` | Compare Years page (`/compare`): pick two years, see global CO2 / CO2-per-person / renewables / temperature deltas | Done |
| `pages/ai_footprint.py` | AI Footprint page (`/ai-footprint`): model/use-case/frequency controls, free-text prompt override, per-capita comparison, CSV download | Done |
| `tests/` | 51 unit tests covering the cleaning rules, analysis helpers, capitals reference, cache-building, chart helpers, and the AI footprint reference-table integrity and analysis helpers | Done |
| `requirements.txt`, `Procfile` | gunicorn entry point (`app:server`) | Done |

## Data sources

**Primary** — Our World in Data, CO₂ and Greenhouse Gas Emissions
`https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv`
50,411 rows × 79 columns. One row per entity per year. Key: `(country, year)`.
254 entities: 218 real countries with ISO-3 codes, 36 aggregates. Years 1750–2024.
CC BY 4.0.

**Supporting** — NASA GISTEMP v4 Land-Ocean Temperature Index
`https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv`
Annual mean anomaly vs 1951–1980. Use the `J-D` column. Public domain.
Two quirks: one preamble line above the header (`skiprows=1`), and missing
values written as asterisks (coerce with `pd.to_numeric(errors="coerce")`).

**Q4 addition** — Our World in Data, Energy
`https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv`
Same publisher, license (CC BY 4.0), and `country`/`iso_code`/`year` key as
the CO2 file, so `filter_countries` applies unchanged. Used for
`renewables_share_elec` (see rule 7).

**Q4 addition** — NASA POWER solar/wind climatology, cached
`https://power.larc.nasa.gov/api/temporal/climatology/point`
Fetched once per country capital by `scripts/build_climatology_cache.py` and
committed as `data/power_climatology.csv`. The running app never calls this
API — it only reads the cached CSV. Public domain.

## Cleaning rules — implement once in `data/`, never in a chart

These came out of a measured profile of the file. They are not optional.

1. **Filter aggregates before any country-level chart.**
   `df[df.iso_code.notna() & (df.iso_code.str.len() == 3)]`
   Rows such as `World`, `Asia`, `European Union (27)`, the World Bank income
   groups, and `International aviation` have no ISO code. Leaving them in
   double-counts emissions and puts "World" at the top of every ranking. This
   is the most common failure with this dataset.

2. **GDP ends at 2022** and is 27% missing. Cap any GDP chart at 2022 and say
   so in the subtitle. Do not extrapolate.

3. **`coal_co2` (38% missing), `gas_co2` (44%), `consumption_co2` (45%)** are
   sparse, concentrated in small and low-income countries. Use for a top-20
   view only. Never `fillna(0)` — that reports an unmeasured country as a
   zero-emitting one.

4. **Default the date slider to 1990–2024.** Coverage before ~1950 is thin.
   Leave the full range selectable for the cumulative-emissions view.

5. **`temperature_change_from_co2` is modelled attribution, not measured
   temperature.** Label it as modelled. Observed warming comes from GISTEMP
   only. Conflating them is a factual error, not a labelling slip.

6. **Exclude countries under 1M population from per-capita rankings.**
   Otherwise the top ten is entirely small petro-states — true, but uninformative.

7. **Use `renewables_share_elec`, not `renewables_share_energy`, for Q4.**
   Verified against the live energy file: `renewables_share_energy` is
   non-null for only 79 of 220 countries, and that count is identical in
   every year from 2015-2023 — it isn't tracking per-country, per-year
   reality. `renewables_share_elec` is non-null for 210-212 of 220 countries
   and varies sensibly year to year. Its own coverage drops off after 2023
   (195/199 reporting in 2024, vs 210-212/220 in 2020-2023), so the Q4 year
   slider is capped at `ENERGY_MAX_YEAR = 2023`.

## Scope constraint

The original project overview promised a choropleth of *regional temperature
anomalies*. That is not achievable from these sources: the emissions file has
no observed temperature, GISTEMP publishes global/hemispheric/zonal means
rather than country values, and Berkeley Earth's country series stops in 2013.

**The map shows emissions. Temperature is a global line chart only.**
If a temperature map is wanted later, use GISTEMP zonal means as latitude bands.

## The four research questions

Q1-Q3 selected from five candidates on data support and visual
distinctiveness; Q4 was added afterward once the OWID Energy dataset and a
NASA POWER climatology cache were available.

- **Q1** — Has global CO₂ growth slowed since 2000?
  Dual-axis line (CO₂ + GISTEMP anomaly), plus a growth-rate bar chart.
- **Q2** — Who emits most in total, versus per person?
  Choropleth + paired horizontal bar charts. The gap between the two rankings
  is the clearest insight in this dataset.
- **Q3** — Does higher GDP still mean higher emissions per person?
  Bubble scatter, log x-axis, population as size, capped at 2022.
- **Q4** — Is renewable electricity adoption tracking natural solar/wind
  potential? Bubble scatter (solar or wind potential vs renewable
  electricity share), sized by population, with the countries furthest
  above and below the trend line labelled.

## Next task

Deploy to Render.

The Dash app is a multi-page app (`app.py` + `pages/`), built on the `data/`
package (cleaning, tested under `tests/`), `prototype_charts.py` and
`q4_charts.py` (chart functions), `state.py` (load-once data), `analysis.py`
(numeric helpers: Q1 trend helpers, plus generic country-series/
year-comparison helpers), `requirements.txt`, and `Procfile`
(`gunicorn app:server`) — all verified locally with `python app.py`.

- Repo is on GitHub at `lavanyas14205/DV-lab-project` (remote `origin`, branch `main`). Create a Render Web Service from it.
- Build command `pip install -r requirements.txt`, start command
  `gunicorn app:server` — no env vars or API keys needed.
- After deploy, sanity-check the live URL: all eight pages (`/`, `/q1`,
  `/q2`, `/q3`, `/q4`, `/country`, `/compare`, `/overview`, `/ai-footprint`, plus the `/` Dashboard landing page) load, every
  slider/dropdown/toggle updates its charts, and the CSV download buttons on
  Q2/Q3/Q4 work.

## Constraints

- Free tier only. No paid services, no API keys.
- Keep it readable — this is graded coursework and will be explained in a viva.
  Prefer clear code over clever code, and comment the non-obvious parts
  (the aggregate filter, the GISTEMP parsing quirks).
- Cite all data sources (OWID CO2, OWID Energy, GISTEMP, NASA POWER) in the
  app footer and the README.
