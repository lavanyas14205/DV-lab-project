# Dataset Report — Global Climate Trends Dashboard

This report documents the datasets used in the project: what type of data
each one is, where it comes from, what it contains, and why it was chosen
over alternatives.

---

## 1. Overview

The dashboard answers four research questions about CO₂ emissions, observed
global warming, and the renewable-energy transition. No synthetic or
hand-generated data is used for the core analysis — every chart is built on
real, publicly published, licensed datasets from government or research
institutions. One additional table (AI-model environmental footprint) is a
curated reference table rather than a measured dataset; this is called out
explicitly below since it is a different kind of source.

| # | Dataset | Type | Publisher | License | Used for |
|---|---|---|---|---|---|
| 1 | OWID CO₂ and Greenhouse Gas Emissions | Tabular, panel (country × year) | Our World in Data | CC BY 4.0 | Q1, Q2, Q3, Country Profile, Compare Years |
| 2 | NASA GISTEMP v4 | Tabular, time series (year) | NASA GISS | Public domain | Q1 |
| 3 | OWID Energy | Tabular, panel (country × year) | Our World in Data | CC BY 4.0 | Q4 |
| 4 | NASA POWER solar/wind climatology (cached) | Tabular, cross-sectional (country) | NASA POWER | Public domain | Q4 |
| 5 | AI-model footprint reference table | Tabular, curated/modeled reference | This project (derived from published estimates) | N/A — original compilation | AI Footprint page |

---

## 2. OWID CO₂ and Greenhouse Gas Emissions (primary dataset)

- **Type**: Tabular panel data — one row per country (or aggregate) per year.
- **Source**: Our World in Data (OWID), sourced in turn from the Global
  Carbon Project.
  `https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv`
- **License**: CC BY 4.0 (free to use with attribution).
- **Size**: 50,411 rows × 79 columns.
- **Coverage**: Years 1750–2024. 254 distinct entities: 218 real countries
  (each with an ISO-3 code) plus 36 aggregate rows (e.g. `World`, `Asia`,
  `European Union (27)`, World Bank income groups).
- **Key columns used**: `country`, `iso_code`, `year`, `co2`,
  `co2_per_capita`, `population`, `gdp`, `coal_co2`, `gas_co2`,
  `consumption_co2`, `temperature_change_from_co2`.
- **Why this dataset**: It is the most complete, actively maintained,
  publicly licensed emissions dataset available, and it already bundles
  population and GDP in the same file. That means Q1–Q3 need only *one*
  source instead of joining separate emissions, population, and GDP
  tables — which minimizes join and misalignment risk.
- **Known quirks (handled in `data/co2.py`, documented in full in
  `CLAUDE.md`)**: aggregate rows must be filtered out by ISO-3 code before
  any country-level chart (otherwise "World" tops every ranking); GDP is 27%
  missing and stops in 2022; `coal_co2`/`gas_co2`/`consumption_co2` are
  38–45% missing and must never be filled with 0; `temperature_change_from_co2`
  is a *modelled* attribution, not an observed temperature.

## 3. NASA GISTEMP v4 (Land-Ocean Temperature Index)

- **Type**: Tabular time series — one row per year, global mean.
- **Source**: NASA Goddard Institute for Space Studies (GISS).
  `https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv`
- **License**: Public domain (U.S. government work).
- **Coverage**: Annual global mean temperature anomaly vs. the 1951–1980
  baseline. The `J-D` (annual mean) column is used.
- **Why this dataset**: It is the **observed** counterpart to the OWID
  file's modelled `temperature_change_from_co2` column. Using an
  independent, authoritative, measured temperature record — rather than
  relying on the modelled attribution already present in the CO₂ file — is
  what lets Q1 honestly distinguish "modelled" from "observed" warming.
- **Known quirks**: one preamble line above the header (loaded with
  `skiprows=1`); missing values are written as `*` in the source file and
  must be coerced with `pd.to_numeric(errors="coerce")`.

## 4. OWID Energy

- **Type**: Tabular panel data — one row per country per year.
- **Source**: Our World in Data.
  `https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv`
- **License**: CC BY 4.0.
- **Key column used**: `renewables_share_elec` (renewable share of
  electricity generation).
- **Why this dataset**: Added specifically for Q4, which needed a
  renewable-adoption metric that the CO₂ file doesn't contain. It shares
  the same publisher, license, and `country`/`iso_code`/`year` key as the
  CO₂ file, so the existing aggregate-row filter applies unchanged — no new
  cleaning logic was needed, only a new loader.
- **Known quirk**: `renewables_share_energy` (share of *total* energy) looks
  like the obvious column but was rejected after profiling — it is non-null
  for only 79 of 220 countries and that count doesn't change at all between
  2015 and 2023, meaning it isn't tracking real per-country change.
  `renewables_share_elec` (share of *electricity*) covers 210–212 of 220
  countries and varies sensibly year to year, so it is the metric actually
  used. Its own coverage drops after 2023, so the Q4 year slider is capped
  at 2023.

## 5. NASA POWER Solar/Wind Climatology (cached)

- **Type**: Tabular, cross-sectional — one row per country, each row a
  multi-year average (climatology), not a real-time reading.
- **Source**: NASA POWER (Prediction of Worldwide Energy Resources) API.
  `https://power.larc.nasa.gov/api/temporal/climatology/point`
- **License**: Public domain.
- **How it enters the project**: Fetched once per country capital
  (`data/capitals.csv`, 218 rows) by the one-time, offline script
  `scripts/build_climatology_cache.py`, and committed as
  `data/power_climatology.csv`. The deployed app only ever reads this cached
  CSV — it makes zero live calls to NASA POWER, which avoids the API's rate
  limits and removes any dependency on an external service staying up.
- **Why this dataset**: Q4 asks whether renewable *adoption* is tracking
  natural *potential*. Answering that requires a physical solar/wind
  potential number, which no OWID file provides — NASA POWER is the only
  free, no-API-key source of long-run solar irradiance and wind-speed
  climatology per location.

## 6. AI-model footprint reference table (supporting page, not core analysis)

- **Type**: Curated reference table, not a primary measured dataset.
- **Source**: `data/ai_footprint.csv`, compiled for this project. Anchored
  to two published figures from MIT News, "Explained: Generative AI's
  environmental impact" (Jan 2025): a ChatGPT query uses roughly 5× the
  electricity of a basic web search, and data centers require roughly 2
  liters of water per kWh consumed for cooling. Cross-checked for
  plausible order of magnitude against the ClimateAligned AI Footprint
  Calculator's published GPT-4o figures.
- **Why it's flagged separately**: Every other dataset in this project is a
  primary, publicly measured source. This one is explicitly **modeled**,
  not measured — there is no standardized, comprehensive measurement of
  per-query AI energy/carbon/water cost. The model-to-model multipliers
  (Claude, Gemini, Grok relative to a ChatGPT baseline) are this project's
  own rough, qualitative estimate, not a citation. This caveat is shown to
  users directly in the AI Footprint page's on-page disclosure banner.
- **Why it's included at all**: It supports one supplementary page
  (`/ai-footprint`) that contextualizes AI energy use against the same
  per-capita framing used elsewhere in the dashboard — but it is kept
  clearly separate from, and never blended into, the four core research
  questions, which rely only on measured data.

---

## 7. Why four (five) sources instead of one all-in-one dataset

No single publicly available dataset contains emissions, GDP, population,
renewable-electricity share, and solar/wind climatology together. The two
OWID files share a publisher, license, and key schema by design, which keeps
joining them trivial; GISTEMP and NASA POWER are brought in only where OWID
has a genuine gap — observed temperature, and physical renewable potential —
not duplicated for the sake of citing more sources.

## 8. Citation

- Our World in Data — CO₂ and Greenhouse Gas Emissions (CC BY 4.0)
- Our World in Data — Energy (CC BY 4.0)
- NASA GISS — GISTEMP v4 (public domain)
- NASA POWER — Solar/Wind Climatology (public domain)

All four are cited in the running app's footer and in `README.md`.
