# Climate Dashboard Expansion — Design Spec

Date: 2026-09-06
Status: approved by user, pending implementation plan

## Context

The Week 4 Dash app (`data.py`, `prototype_charts.py`, `app.py`, tested,
deployed-ready) already answers the three research questions in `CLAUDE.md`:
CO2 growth trend, total vs per-capita emitters, GDP vs emissions. It works
and was verified locally in a browser.

This is still coursework, but the user wants to go beyond the minimum
three-question scope for a stronger submission: more datasets, deeper
analysis, and a more polished multi-page structure rather than one long
scrolling page.

## Goals

- Add a fourth research question: **is renewable energy adoption tracking
  each country's natural solar/wind potential?**
- Add a quantitative trend read to Q1 (not just "the bars look smaller").
- Restructure the single-page app into a multi-page Dash app: an overview
  page plus one page per research question.
- Do all of this without breaking or meaningfully risking the existing,
  working Q1–Q3 dashboard.

## Non-goals

- No new hosting requirements — still Render free tier, still no API keys,
  still no paid services.
- No shared cross-page state (e.g. one global year selector). Each page
  keeps its own controls; simpler, and avoids a class of Dash multi-page
  state bugs.
- No live network calls from the running app for the new NASA POWER data —
  it's pre-fetched and cached to a file, once, offline.
- Not attempting country-level observed temperature (unchanged from the
  original scope constraint already in `CLAUDE.md` — GISTEMP has no
  country-level series; POWER's climatology is solar/wind, not temperature
  anomaly, and doesn't change that constraint).

## Architecture overview

```
data/
  __init__.py            # load_all() — orchestrates every loader below
  co2.py                 # OWID CO2 loading + cleaning rules 1, 2, 3, 6 (moved from data.py)
  gistemp.py             # GISTEMP loading + rule 5's constant (moved from data.py)
  energy.py              # NEW — OWID Energy dataset loading
  climatology.py         # NEW — reads the cached solar/wind CSV; no network code
  capitals.csv           # NEW — static reference: iso_code, capital, lat, lon
  power_climatology.csv  # NEW — cached output of scripts/build_climatology_cache.py
scripts/
  build_climatology_cache.py   # NEW — one-time, offline: capitals.csv -> NASA POWER -> data/power_climatology.csv
prototype_charts.py      # existing Q1-Q3 chart functions — untouched
q4_charts.py             # NEW — renewable potential vs adoption chart
app.py                   # becomes the multi-page shell: nav + use_pages=True
state.py                 # NEW — holds the frames loaded once by app.py, imported by pages/ to avoid circular imports
pages/
  overview.py            # NEW — narrative landing page, headline stats
  q1_growth.py           # existing Q1 charts + new trend overlay, as a page
  q2_emitters.py         # existing Q2 charts, as a page
  q3_gdp.py              # existing Q3 chart, as a page
  q4_renewables.py       # NEW — Q4 page
tests/
  test_co2.py            # existing cleaning-rule tests, relocated
  test_gistemp.py        # existing cleaning-rule tests, relocated
  test_energy.py         # NEW
  test_climatology.py    # NEW
```

`data.py`, the current single-file module, is replaced by the `data/`
package above. `profile_dataset.py` continues to import from `data` — its
own content doesn't change beyond that import path.

## Data layer

### Existing sources (unchanged behavior, relocated)

- OWID CO2 (`data/co2.py`): cleaning rules 1, 2, 3, 6 from `CLAUDE.md`,
  currently in `data.py`, move verbatim.
- GISTEMP (`data/gistemp.py`): the skiprows/asterisk handling, currently in
  `data.py`, move verbatim.

### New: OWID Energy dataset (`data/energy.py`)

Source: `https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv`
(same publisher, same CC BY 4.0 license, same `country`/`iso_code`/`year`
key as the CO2 file — `filter_countries()` from `data/co2.py` applies to it
unchanged).

**Rule 7 (new):** use `renewables_share_elec`, not `renewables_share_energy`.
Verified against the live file: `renewables_share_energy` (renewable share
of *total* energy) is non-null for only 79 of 220 countries, and that count
is identical in every year from 2015–2023 — it isn't really tracking
per-country, per-year reality. `renewables_share_elec` (renewable share of
*electricity generation*) is non-null for 210–212 of 220 countries and
varies sensibly year to year. `data/energy.py` documents this rule the same
way `data/co2.py` documents rules 1–6, and only exposes the electricity
figure for charting.

### New: capital coordinates (`data/capitals.csv`)

A static reference table (`iso_code, capital, lat, lon`) for the 218
countries in the OWID data. There is no free, key-less lookup left standing
for this — `restcountries.com`'s legacy free API is deprecated as of this
check; its replacement requires their newer signup flow. Since capital
coordinates are fixed geography, not something that needs a live source,
this file will be authored directly (from general geographic knowledge, the
same kind of public-domain fact you'd find in a gazetteer) rather than
fetched. It's approximate by construction — a capital-city point standing in
for "the country" — and will say so in a comment at the top of the file and
in `data/climatology.py`'s docstring, so this is an honest, explainable
approximation in the viva rather than a hidden one.

### New: NASA POWER solar/wind climatology (`data/power_climatology.csv`, `data/climatology.py`)

Endpoint (verified live, no API key):

```
https://power.larc.nasa.gov/api/temporal/climatology/point
  ?parameters=ALLSKY_SFC_SW_DWN,WS10M&community=RE&longitude={lon}&latitude={lat}&format=JSON
```

Returns 20-year (2001–2020) monthly + annual averages for all-sky surface
shortwave irradiance (`ALLSKY_SFC_SW_DWN`, kWh/m²/day — solar potential) and
wind speed at 10m (`WS10M`, m/s — wind potential), keyed by the `ANN`
(annual) value in the JSON response.

`scripts/build_climatology_cache.py` (one-time, run manually, **never**
invoked by the deployed app):

1. Reads `data/capitals.csv`.
2. For each country not already present in `data/power_climatology.csv`,
   calls the endpoint above via `urllib` (stdlib — this script is not a
   runtime dependency of the app, so it doesn't need `requests` added to
   `requirements.txt`).
3. Appends the result (`iso_code, solar_kwh_per_m2_day, wind_speed_ms`) to
   the cache file.
4. On a request failure for one country: log it and continue — don't abort
   the run. Because step 2 skips rows already cached, rerunning the script
   after a partial failure only fetches what's missing.

`data/climatology.py` does nothing but read the finished CSV. No network
code runs in the request path, and no network code runs at app startup
either — only this offline script talks to NASA.

## Charts

### Q1 trend overlay (`pages/q1_growth.py`, building on `prototype_charts.co2_growth_rate_bar`)

Add a 5-year rolling average line on top of the existing growth-rate bars,
plus a text annotation comparing mean growth 1990–1999 vs 2015–2024 — a
number, not just a visual impression, answering "has it slowed" directly.

### Q4: renewable potential vs adoption (`q4_charts.py`)

A bubble scatter: x = solar irradiance or wind speed, y =
`renewables_share_elec` from `data/energy.py`, sized by population (the
energy dataset carries its own `population` column, same OWID entity
convention as the CO2 file). **Correction from an earlier draft of this
spec:** no color-by-continent — verified neither the CO2 nor the Energy
CSV has a continent column (the existing `gdp_emissions_bubble` in
`prototype_charts.py` already has a defensive
`"continent" if "continent" in frame.columns else None` that silently
never triggers today; Q4 won't repeat that dead branch). A
`dcc.RadioItems` control on the page (Solar / Wind) picks which
`data/climatology.py` column feeds the x-axis, same pattern as the
existing Q2 map's total/per-capita toggle.

Countries far below the trend (high potential, low adoption) and far above
it (low potential, high adoption via hydro/imports/policy) are the
interesting story: fit a simple linear trend across the plotted points, take
the 3 largest positive and 3 largest negative residuals, and label those 6
countries by name on the chart.

## App structure

- `app.py`: loads all data once via `data.load_all()` into `state.py`,
  constructs `Dash(__name__, use_pages=True)`, renders a top nav (Overview /
  Q1 / Q2 / Q3 / Q4) and `dash.page_container`.
- Each `pages/qN_*.py` calls `dash.register_page(__name__, path=...)` and
  owns its own layout and callbacks, reading shared frames from `state.py`.
- `pages/overview.py`: states all four research questions, headline stats
  (latest-year global CO2, latest temperature anomaly, current top emitter,
  most-improved renewable adopter), and links into each page.
- CSV download stays a per-page control, same mechanism as the current
  single-page app (each page downloads its own filtered view).

## Testing

- `tests/test_co2.py`, `tests/test_gistemp.py`: the existing 7 tests,
  relocated to match the new module split, unchanged in substance.
- `tests/test_energy.py` (new): proves `renewables_share_elec` is what gets
  exposed (not `renewables_share_energy`), and that `filter_countries`
  applies cleanly to the energy frame.
- `tests/test_climatology.py` (new): parsing of the cached CSV format.
- The JSON-parsing step inside `build_climatology_cache.py` (pulling `ANN`
  out of the POWER response) is factored into a small pure function and
  tested against a fixture response — same pattern as `data.parse_gistemp`.
  The network-calling part of the script itself is not unit-tested
  (one-time utility, exception category already agreed for this project).
- Chart functions (`prototype_charts.py` additions, `q4_charts.py`) are
  verified against real data and in-browser, not unit-tested — consistent
  with how Q1–Q3 were already verified.

## Error handling / edge cases

- A country missing from `data/power_climatology.csv` (failed fetch, or not
  in `capitals.csv`) is silently excluded from the Q4 chart via an inner
  join — expected and documented, not an error state. Roughly 218 countries
  are expected; a handful missing is acceptable.
- `build_climatology_cache.py` is idempotent and resumable, per above.

## Deployment

No change to the Render deployment plan already in `CLAUDE.md`: push to
GitHub, `pip install -r requirements.txt`, `gunicorn app:server`. No new
runtime dependencies (Dash's `pages` feature and `dash.page_container` are
part of the `dash` package already required). `data/power_climatology.csv`
and `data/capitals.csv` are committed to the repo so the deployed app never
needs to reach NASA at all.
