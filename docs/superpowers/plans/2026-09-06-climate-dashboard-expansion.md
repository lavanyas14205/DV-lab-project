# Climate Dashboard Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the working Q1-Q3 climate dashboard into a 4-question, multi-page Dash app: add a renewable-potential-vs-adoption question (OWID Energy + NASA POWER solar/wind climatology), a quantitative trend read on Q1, and a proper multi-page structure with an overview landing page.

**Architecture:** Split the single `data.py` into a `data/` package (`co2.py`, `gistemp.py`, `energy.py`, `climatology.py`) behind one `load_all()` returning a `LoadedData` dataclass. Fetch NASA POWER data once, offline, into a checked-in CSV (`data/power_climatology.csv`) via `scripts/build_climatology_cache.py` — the running app never calls NASA. Rebuild `app.py` as a thin multi-page shell (`use_pages=True`) with one `pages/*.py` module per question, each owning its own controls and callbacks, sharing loaded data via `state.py`.

**Tech Stack:** Python 3.11, pandas, Plotly (`plotly.express`, `graph_objects`, `subplots`), Dash 4.4.1 (multi-page: `dash.register_page`, `dash.page_container`, `dash.page_registry` — confirmed present and working on the installed version), pytest, numpy (already a pandas dependency, used for `np.polyfit`), stdlib `urllib`/`csv`/`json` for the offline NASA POWER script (no new runtime dependency).

**Spec:** `docs/superpowers/specs/2026-09-06-climate-dashboard-expansion-design.md`

## Global Constraints

- Free tier only. No paid services, no API keys (from `CLAUDE.md` and the spec's Non-goals — NASA POWER and OWID Energy are both confirmed key-less).
- Load data once at startup; never re-fetch inside a callback. Extended by this expansion: NASA POWER is not called even at startup — only by the offline `scripts/build_climatology_cache.py`, which is never invoked by the deployed app.
- Keep it readable — this is graded coursework explained in a viva. Comment the non-obvious parts (aggregate filter, GISTEMP parsing quirks, rule 7's column choice, the capitals.csv approximation).
- Cite every data source in the app footer and the README (OWID CO2, OWID Energy, NASA GISTEMP, NASA POWER).
- No shared cross-page state — each page keeps its own year slider / controls (spec's Non-goals).
- `filter_countries()` (rule 1, ISO-3 code check) is the one function every source with a `country`/`iso_code` key runs through before country-level charting — never re-implement it per source.

---

### Task 1: Split `data.py` into a `data/` package

**Files:**
- Create: `data/__init__.py`, `data/co2.py`, `data/gistemp.py`
- Create: `tests/test_co2.py`, `tests/test_gistemp.py`
- Modify: `app.py:15`, `profile_dataset.py:43`
- Delete: `data.py`, `tests/test_data.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: `data.load_all(co2_path=..., gistemp_path=...) -> LoadedData` where `LoadedData` has fields `co2_all: pd.DataFrame`, `co2_countries: pd.DataFrame`, `temperature: pd.DataFrame`. Also re-exports (unchanged names/signatures) `data.CO2_URL`, `data.GISTEMP_URL`, `data.DEFAULT_YEAR_RANGE`, `data.GDP_MAX_YEAR`, `data.MIN_POPULATION_FOR_PER_CAPITA`, `data.SPARSE_EMISSIONS_COLUMNS`, `data.MODELLED_TEMPERATURE_COLUMN`, `data.filter_countries`, `data.cap_year`, `data.filter_min_population`, `data.load_co2_data`, `data.load_temperature_data`, `data.parse_gistemp`. Every later task imports these the same way existing code already does (`import data; data.filter_countries(...)`, etc.) — nothing about the public `data.*` surface changes, only its internal layout.

This is a pure refactor (move, not behavior change), so the "red" step is "confirm the 7 existing tests are green before touching anything," and the "green" step is "confirm they're still green after the move with new import paths."

- [ ] **Step 1: Confirm the existing tests pass before changing anything**

Run: `pytest tests/test_data.py -v`
Expected: 7 passed (this is the baseline — if this doesn't pass, stop and investigate before refactoring).

- [ ] **Step 2: Create the `data/` package directory and `data/co2.py`**

```python
"""OWID CO2 data loading and cleaning.

Cleaning rules below (and nowhere else) come from a measured profile of
this file. See CLAUDE.md for the numbers that justify each one.
"""

import pandas as pd

CO2_URL = "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv"

# Rule 4: coverage before ~1950 is thin, so the UI defaults here. Full range
# stays selectable for the cumulative-emissions view.
DEFAULT_YEAR_RANGE = (1990, 2024)

# Rule 2: GDP is 27% missing and stops being reported after 2022.
GDP_MAX_YEAR = 2022

# Rule 6: below this, per-capita rankings are dominated by small petro-states.
MIN_POPULATION_FOR_PER_CAPITA = 1_000_000

# Rule 3: sparse enough (38-45% missing) that they're only meaningful as a
# top-20 view, and must never be filled with 0 (that reports "unmeasured"
# as "zero-emitting").
SPARSE_EMISSIONS_COLUMNS = ["coal_co2", "gas_co2", "consumption_co2"]

# Rule 5: this is modelled attribution, not an observation. Any chart using
# it must be labelled "modelled" — observed warming comes from GISTEMP only.
MODELLED_TEMPERATURE_COLUMN = "temperature_change_from_co2"


def filter_countries(df: pd.DataFrame) -> pd.DataFrame:
    """Drop aggregate rows (World, continents, income groups) — rule 1.

    These rows have no ISO-3 code. Leaving them in double-counts emissions
    and puts "World" at the top of every ranking.
    """
    return df[df["iso_code"].notna() & (df["iso_code"].str.len() == 3)]


def cap_year(df: pd.DataFrame, max_year: int = GDP_MAX_YEAR) -> pd.DataFrame:
    """Cap a frame at max_year — rule 2. Do not extrapolate past it."""
    return df[df["year"] <= max_year]


def filter_min_population(
    df: pd.DataFrame, min_population: int = MIN_POPULATION_FOR_PER_CAPITA
) -> pd.DataFrame:
    """Exclude countries under min_population from per-capita views — rule 6."""
    return df[df["population"] >= min_population]


def load_co2_data(path_or_url: str = CO2_URL) -> pd.DataFrame:
    return pd.read_csv(path_or_url)
```

- [ ] **Step 3: Create `data/gistemp.py`**

```python
"""NASA GISTEMP v4 loading and parsing."""

import pandas as pd

GISTEMP_URL = "https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv"


def parse_gistemp(raw: pd.DataFrame) -> pd.DataFrame:
    """Turn a raw (already skiprows=1) GISTEMP frame into (year, anomaly).

    Missing values are written as "*" in the source file, so J-D must be
    coerced rather than read as numeric directly.
    """
    out = raw[["Year", "J-D"]].rename(
        columns={"Year": "year", "J-D": "temperature_anomaly"}
    )
    out["temperature_anomaly"] = pd.to_numeric(
        out["temperature_anomaly"], errors="coerce"
    )
    return out


def load_temperature_data(path_or_url: str = GISTEMP_URL) -> pd.DataFrame:
    # One preamble line above the header row.
    raw = pd.read_csv(path_or_url, skiprows=1)
    return parse_gistemp(raw)
```

- [ ] **Step 4: Create `data/__init__.py`**

```python
"""Shared loading and cleaning for the Global Climate Trends dashboard.

Package layout: co2.py and gistemp.py hold source-specific loading and
cleaning; this file just orchestrates them behind load_all().
"""

from dataclasses import dataclass

import pandas as pd

from .co2 import (
    CO2_URL,
    DEFAULT_YEAR_RANGE,
    GDP_MAX_YEAR,
    MIN_POPULATION_FOR_PER_CAPITA,
    MODELLED_TEMPERATURE_COLUMN,
    SPARSE_EMISSIONS_COLUMNS,
    cap_year,
    filter_countries,
    filter_min_population,
    load_co2_data,
)
from .gistemp import GISTEMP_URL, load_temperature_data, parse_gistemp

__all__ = [
    "CO2_URL", "GISTEMP_URL", "DEFAULT_YEAR_RANGE", "GDP_MAX_YEAR",
    "MIN_POPULATION_FOR_PER_CAPITA", "SPARSE_EMISSIONS_COLUMNS",
    "MODELLED_TEMPERATURE_COLUMN", "cap_year", "filter_countries",
    "filter_min_population", "load_co2_data", "load_temperature_data",
    "parse_gistemp", "LoadedData", "load_all",
]


@dataclass
class LoadedData:
    co2_all: pd.DataFrame
    co2_countries: pd.DataFrame
    temperature: pd.DataFrame


def load_all(co2_path: str = CO2_URL, gistemp_path: str = GISTEMP_URL) -> LoadedData:
    """Load once at startup. Returns every frame the app needs."""
    co2_all = load_co2_data(co2_path)
    co2_countries = filter_countries(co2_all)
    temperature = load_temperature_data(gistemp_path)
    return LoadedData(co2_all=co2_all, co2_countries=co2_countries, temperature=temperature)
```

- [ ] **Step 5: Delete the old `data.py`**

Run: `rm data.py`

(Must happen before running anything that does `import data` — a stray `data.py` next to the new `data/` package is ambiguous and must not exist.)

- [ ] **Step 6: Create `tests/test_co2.py`** (the 4 CO2-related tests from the old `tests/test_data.py`, import path updated)

```python
import pandas as pd

from data.co2 import (
    GDP_MAX_YEAR,
    MIN_POPULATION_FOR_PER_CAPITA,
    cap_year,
    filter_countries,
    filter_min_population,
)


def test_filter_countries_drops_rows_with_no_iso_code():
    df = pd.DataFrame(
        {
            "country": ["Afghanistan", "World", "Africa"],
            "iso_code": ["AFG", None, None],
            "year": [2020, 2020, 2020],
        }
    )

    result = filter_countries(df)

    assert list(result["country"]) == ["Afghanistan"]


def test_filter_countries_drops_aggregates_with_non_iso3_codes():
    df = pd.DataFrame(
        {
            "country": ["Afghanistan", "European Union (27)"],
            "iso_code": ["AFG", "OWID_EU27"],
            "year": [2020, 2020],
        }
    )

    result = filter_countries(df)

    assert list(result["country"]) == ["Afghanistan"]


def test_cap_year_excludes_rows_after_gdp_max_year():
    df = pd.DataFrame({"year": [2021, 2022, 2023], "gdp": [1, 2, 3]})

    result = cap_year(df)

    assert list(result["year"]) == [2021, 2022]
    assert GDP_MAX_YEAR == 2022


def test_filter_min_population_excludes_small_countries():
    df = pd.DataFrame(
        {
            "country": ["Palau", "India"],
            "population": [18_000, 1_400_000_000],
        }
    )

    result = filter_min_population(df)

    assert list(result["country"]) == ["India"]
    assert MIN_POPULATION_FOR_PER_CAPITA == 1_000_000
```

- [ ] **Step 7: Create `tests/test_gistemp.py`** (the 3 GISTEMP-related tests from the old file, import path updated)

```python
import pandas as pd

from data.gistemp import load_temperature_data, parse_gistemp


def test_parse_gistemp_renames_and_selects_annual_column():
    raw = pd.DataFrame(
        {
            "Year": [1880, 1881],
            "Jan": [-0.19, -0.20],
            "J-D": ["-.17", "-.09"],
        }
    )

    result = parse_gistemp(raw)

    assert list(result.columns) == ["year", "temperature_anomaly"]
    assert list(result["year"]) == [1880, 1881]


def test_parse_gistemp_coerces_asterisk_placeholders_to_nan():
    raw = pd.DataFrame({"Year": [2024, 2025], "J-D": ["1.20", "***"]})

    result = parse_gistemp(raw)

    assert result["temperature_anomaly"].iloc[0] == 1.20
    assert pd.isna(result["temperature_anomaly"].iloc[1])


def test_load_temperature_data_skips_gistemp_preamble_line(tmp_path):
    csv_text = (
        "Land-Ocean: Global Means\n"
        "Year,Jan,J-D\n"
        "1880,-.19,-.17\n"
        "1881,-.20,-.09\n"
    )
    path = tmp_path / "gistemp.csv"
    path.write_text(csv_text)

    result = load_temperature_data(str(path))

    assert list(result["year"]) == [1880, 1881]
    assert list(result["temperature_anomaly"]) == [-0.17, -0.09]
```

- [ ] **Step 8: Delete the old test file**

Run: `rm tests/test_data.py`

- [ ] **Step 9: Update `app.py`'s data-loading line**

Current line 15 reads:
```python
CO2_ALL, CO2_COUNTRIES, TEMPERATURE = data.load_all()
```
Replace with:
```python
_loaded = data.load_all()
CO2_ALL, CO2_COUNTRIES, TEMPERATURE = _loaded.co2_all, _loaded.co2_countries, _loaded.temperature
```

- [ ] **Step 10: Update `profile_dataset.py`'s data-loading line**

Current line 43 (inside `main()`) reads:
```python
    co2_all, co2_countries, temperature = data.load_all()
```
Replace with:
```python
    loaded = data.load_all()
    co2_all, co2_countries, temperature = loaded.co2_all, loaded.co2_countries, loaded.temperature
```

- [ ] **Step 11: Run the full test suite**

Run: `pytest tests/ -v`
Expected: 7 passed (`test_co2.py` x4, `test_gistemp.py` x3), same count as the baseline in Step 1, now under new file names.

- [ ] **Step 12: Smoke-test `profile_dataset.py` still produces the same numbers**

Run: `python profile_dataset.py`
Expected: same shape of output as before the refactor (254 entities, 218 countries, 36 aggregates, GDP capped at 2022, sparse-column percentages, population count) — the numbers themselves may drift slightly if OWID has updated the file since, but the structure and rough magnitudes should match.

- [ ] **Step 13: Smoke-test the app still boots**

Run: `python app.py` in the background, then `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8050/` (expect `200`), then stop the server.

- [ ] **Step 14: Commit**

```bash
git add data/ app.py profile_dataset.py tests/test_co2.py tests/test_gistemp.py
git rm data.py tests/test_data.py
git commit -m "Split data.py into a data/ package (co2.py, gistemp.py)"
```

---

### Task 2: Add the OWID Energy dataset

**Files:**
- Create: `data/energy.py`, `tests/test_energy.py`
- Modify: `data/__init__.py`, `profile_dataset.py`

**Interfaces:**
- Consumes: `data.co2.filter_countries` (Task 1) — reused unchanged, not reimplemented.
- Produces: `data.energy.load_energy_data(path_or_url=ENERGY_URL) -> pd.DataFrame` (raw, unfiltered, same `country`/`iso_code`/`year` shape as `load_co2_data`); `data.energy.renewable_share(df) -> pd.Series` (the rule-7-correct column); `data.energy.RENEWABLE_SHARE_COLUMN` (`"renewables_share_elec"`); `data.energy.ENERGY_MAX_YEAR` (`2023`). `LoadedData` gains a field `energy: pd.DataFrame` (raw, unfiltered — same convention as `co2_all`; callers filter with `data.filter_countries` themselves, matching how `co2_countries` is derived). Later tasks import `from data.energy import RENEWABLE_SHARE_COLUMN, ENERGY_MAX_YEAR, renewable_share` and read `state.loaded.energy`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_energy.py
import pandas as pd

from data.energy import RENEWABLE_SHARE_COLUMN, renewable_share


def test_renewable_share_reads_the_electricity_column_not_total_energy_column():
    """Rule 7: renewables_share_energy is non-null for only 79/220 countries
    and doesn't vary by year in the live file — renewables_share_elec covers
    210-212/220 and is the one that should ever reach a chart."""
    df = pd.DataFrame(
        {
            "renewables_share_elec": [80.0],
            "renewables_share_energy": [10.0],
        }
    )

    result = renewable_share(df)

    assert result.iloc[0] == 80.0
    assert RENEWABLE_SHARE_COLUMN == "renewables_share_elec"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_energy.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'data.energy'`

- [ ] **Step 3: Write `data/energy.py`**

```python
"""OWID Energy dataset loading — renewable adoption for Q4.

Source: https://github.com/owid/energy-data — same publisher, license
(CC BY 4.0), and country/iso_code/year key as data/co2.py, so
filter_countries applies to this frame unchanged.
"""

import pandas as pd

ENERGY_URL = "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv"

# Rule 7: use renewables_share_elec (renewable share of electricity
# generation), not renewables_share_energy (renewable share of total
# energy consumption). Verified against the live file: renewables_share_energy
# is non-null for only 79 of 220 countries, and that count is identical in
# every year from 2015-2023 — it isn't tracking per-country, per-year
# reality. renewables_share_elec is non-null for 210-212 of 220 countries
# and varies sensibly year to year.
RENEWABLE_SHARE_COLUMN = "renewables_share_elec"

# Coverage of RENEWABLE_SHARE_COLUMN drops off after this year (195/199
# countries reporting in 2024, vs 210-212/220 in 2020-2023).
ENERGY_MAX_YEAR = 2023


def renewable_share(df: pd.DataFrame) -> pd.Series:
    """The renewable-adoption metric for Q4 — see rule 7 for why this column,
    not renewables_share_energy."""
    return df[RENEWABLE_SHARE_COLUMN]


def load_energy_data(path_or_url: str = ENERGY_URL) -> pd.DataFrame:
    return pd.read_csv(path_or_url)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_energy.py -v`
Expected: PASS

- [ ] **Step 5: Extend `data/__init__.py` to load the energy frame**

Add to the imports:
```python
from .energy import ENERGY_URL, load_energy_data
```
Add `"ENERGY_URL", "load_energy_data",` to `__all__`.

Change the `LoadedData` dataclass to:
```python
@dataclass
class LoadedData:
    co2_all: pd.DataFrame
    co2_countries: pd.DataFrame
    temperature: pd.DataFrame
    energy: pd.DataFrame
```

Change `load_all` to:
```python
def load_all(
    co2_path: str = CO2_URL,
    gistemp_path: str = GISTEMP_URL,
    energy_path: str = ENERGY_URL,
) -> LoadedData:
    """Load once at startup. Returns every frame the app needs."""
    co2_all = load_co2_data(co2_path)
    co2_countries = filter_countries(co2_all)
    temperature = load_temperature_data(gistemp_path)
    energy = load_energy_data(energy_path)
    return LoadedData(
        co2_all=co2_all, co2_countries=co2_countries, temperature=temperature, energy=energy
    )
```

- [ ] **Step 6: Extend `profile_dataset.py` with an energy-coverage profile (reinforces rule 7 with reproducible evidence, same pattern as `profile_gdp`)**

Add this function:
```python
def profile_energy(energy_all):
    from data.co2 import filter_countries
    from data.energy import ENERGY_MAX_YEAR

    countries = filter_countries(energy_all)
    latest = countries[countries["year"] == ENERGY_MAX_YEAR]
    print(f"\nEnergy dataset, {ENERGY_MAX_YEAR}:")
    print(f"  renewables_share_energy non-null: {latest['renewables_share_energy'].notna().sum()} / {len(latest)}")
    print(f"  renewables_share_elec non-null: {latest['renewables_share_elec'].notna().sum()} / {len(latest)} (rule 7: use this one)")
```

Update `main()`:
```python
def main():
    loaded = data.load_all()
    co2_all, co2_countries, temperature = loaded.co2_all, loaded.co2_countries, loaded.temperature
    profile_entities(co2_all, co2_countries)
    profile_gdp(co2_countries)
    profile_sparse_emissions(co2_countries)
    profile_population(co2_countries)
    profile_energy(loaded.energy)
    print(f"\nGISTEMP rows: {len(temperature)}, "
          f"years {temperature['year'].min()}-{temperature['year'].max()}")
```

- [ ] **Step 7: Run the full test suite**

Run: `pytest tests/ -v`
Expected: 8 passed.

- [ ] **Step 8: Smoke-test `profile_dataset.py` and app boot**

Run: `python profile_dataset.py` — expect the new "Energy dataset, 2023" section showing roughly 79/220 vs 210-212/220.
Run: `python app.py` in background, curl `http://127.0.0.1:8050/` (expect `200`), stop it. (The app now also downloads the energy CSV at startup — confirm this doesn't error or hang.)

- [ ] **Step 9: Commit**

```bash
git add data/energy.py data/__init__.py tests/test_energy.py profile_dataset.py
git commit -m "Add OWID Energy dataset loading (rule 7: renewables_share_elec)"
```

---

### Task 3: Author `data/capitals.csv`

**Files:**
- Create: `data/capitals.csv`, `tests/test_capitals.py`

**Interfaces:**
- Consumes: `data.co2.load_co2_data`, `data.co2.filter_countries` (Task 1) — used only by the test, to determine the exact required ISO-3 list from the live source.
- Produces: `data/capitals.csv` with header `iso_code,country,capital,lat,lon` — one row per ISO-3 country in the live OWID CO2 data, `lat`/`lon` in decimal degrees. Task 4 (`scripts/build_climatology_cache.py`) reads this file directly by path; no Python loader function is needed for it.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_capitals.py
from pathlib import Path

import pandas as pd

from data.co2 import filter_countries, load_co2_data

CAPITALS_PATH = Path(__file__).resolve().parent.parent / "data" / "capitals.csv"


def _load_capitals():
    return pd.read_csv(CAPITALS_PATH)


def test_capitals_file_has_required_columns():
    capitals = _load_capitals()
    assert list(capitals.columns) == ["iso_code", "country", "capital", "lat", "lon"]


def test_capitals_has_no_duplicate_iso_codes():
    capitals = _load_capitals()
    assert capitals["iso_code"].is_unique


def test_capitals_lat_lon_are_within_valid_ranges():
    capitals = _load_capitals()
    assert capitals["lat"].between(-90, 90).all()
    assert capitals["lon"].between(-180, 180).all()


def test_capitals_covers_every_country_in_the_live_co2_dataset():
    """Integration test — needs network access to fetch the live CO2 file."""
    co2_countries = filter_countries(load_co2_data())
    required_iso_codes = set(co2_countries["iso_code"].unique())
    capitals = _load_capitals()
    covered_iso_codes = set(capitals["iso_code"])
    missing = required_iso_codes - covered_iso_codes
    assert not missing, f"capitals.csv is missing: {sorted(missing)}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_capitals.py -v`
Expected: FAIL — `FileNotFoundError` (no `data/capitals.csv` yet).

- [ ] **Step 3: Find the exact list of ISO-3 codes the file must cover**

Run:
```bash
python -c "from data.co2 import load_co2_data, filter_countries; c = filter_countries(load_co2_data()); print(sorted(c['iso_code'].unique().tolist()))"
```
This prints the exact list (218 codes as of the spec being written; may drift slightly if OWID has updated the file — the test in Step 1 is the authority, not this fixed number).

- [ ] **Step 4: Author `data/capitals.csv`**

Write one row per code from Step 3's list, in the format `iso_code,country,capital,lat,lon` — e.g. the file starts:
```csv
iso_code,country,capital,lat,lon
AFG,Afghanistan,Kabul,34.5553,69.2075
ALB,Albania,Tirana,41.3275,19.8189
DZA,Algeria,Algiers,36.7538,3.0588
...
```
Use each country's de jure capital city and its approximate decimal-degree coordinates (general geographic knowledge — this is fixed reference geography, the same kind of fact found in any gazetteer, not something requiring a live source; see the spec's "New: capital coordinates" section for why). Every code from Step 3 must appear exactly once — Step 5's test run is the objective check, not a subjective judgment call.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_capitals.py -v`
Expected: 4 passed. If `test_capitals_covers_every_country_in_the_live_co2_dataset` fails, its assertion message lists exactly which ISO-3 codes are missing — add those rows and rerun.

- [ ] **Step 6: Run the full test suite**

Run: `pytest tests/ -v`
Expected: 12 passed.

- [ ] **Step 7: Commit**

```bash
git add data/capitals.csv tests/test_capitals.py
git commit -m "Add static capital-coordinates reference table"
```

---

### Task 4: Build the NASA POWER climatology cache

**Files:**
- Create: `scripts/__init__.py` (empty), `scripts/build_climatology_cache.py`, `tests/test_build_climatology_cache.py`
- Create (generated by running the script, then committed): `data/power_climatology.csv`

**Interfaces:**
- Consumes: `data/capitals.csv` (Task 3) — read directly by file path, one row per country.
- Produces: `data/power_climatology.csv` with header `iso_code,solar_kwh_per_m2_day,wind_speed_ms`. Task 5's `data/climatology.py` reads this file. Also produces the pure function `scripts.build_climatology_cache.extract_annual_values(power_response: dict) -> tuple[float, float]`, tested directly (no network needed for the test).

- [ ] **Step 1: Create `scripts/__init__.py`**

Empty file (makes `scripts` an importable package so tests can do `from scripts.build_climatology_cache import ...` without path hacks, the same way `from data.co2 import ...` already works).

- [ ] **Step 2: Write the failing test**

```python
# tests/test_build_climatology_cache.py
from scripts.build_climatology_cache import extract_annual_values


def test_extract_annual_values_reads_ann_field_from_power_response():
    """Shape confirmed live against NASA POWER's climatology endpoint:
    https://power.larc.nasa.gov/api/temporal/climatology/point
      ?parameters=ALLSKY_SFC_SW_DWN,WS10M&community=RE&longitude=...&latitude=...&format=JSON
    """
    response = {
        "properties": {
            "parameter": {
                "ALLSKY_SFC_SW_DWN": {"JAN": 2.173, "FEB": 2.969, "ANN": 4.1196},
                "WS10M": {"JAN": 4.65, "FEB": 4.72, "ANN": 3.97},
            }
        }
    }

    solar, wind = extract_annual_values(response)

    assert solar == 4.1196
    assert wind == 3.97
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_build_climatology_cache.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.build_climatology_cache'`

- [ ] **Step 4: Write `scripts/build_climatology_cache.py`**

```python
"""One-time, offline: fetch solar/wind climatology for every capital in
data/capitals.csv from NASA POWER, cache to data/power_climatology.csv.

Run manually: python scripts/build_climatology_cache.py
Never invoked by the deployed app — data/climatology.py only ever reads
the cache file this script produces, so the running app makes zero calls
to NASA, at startup or otherwise.

Uses only the standard library (urllib, csv, json) — this script is not a
runtime dependency of the app, so it doesn't need `requests` added to
requirements.txt.
"""

import csv
import json
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPITALS_PATH = REPO_ROOT / "data" / "capitals.csv"
CACHE_PATH = REPO_ROOT / "data" / "power_climatology.csv"

POWER_URL = (
    "https://power.larc.nasa.gov/api/temporal/climatology/point"
    "?parameters=ALLSKY_SFC_SW_DWN,WS10M&community=RE"
    "&longitude={lon}&latitude={lat}&format=JSON"
)

FIELDNAMES = ["iso_code", "solar_kwh_per_m2_day", "wind_speed_ms"]


def extract_annual_values(power_response: dict) -> tuple:
    """Pull annual solar irradiance and wind speed from a POWER climatology response."""
    params = power_response["properties"]["parameter"]
    solar = params["ALLSKY_SFC_SW_DWN"]["ANN"]
    wind = params["WS10M"]["ANN"]
    return solar, wind


def fetch_climatology(lat: float, lon: float) -> tuple:
    url = POWER_URL.format(lat=lat, lon=lon)
    with urllib.request.urlopen(url, timeout=30) as response:
        payload = json.loads(response.read())
    return extract_annual_values(payload)


def load_capitals() -> list:
    with open(CAPITALS_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_existing_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    with open(CACHE_PATH, newline="", encoding="utf-8") as f:
        return {row["iso_code"]: row for row in csv.DictReader(f)}


def main():
    capitals = load_capitals()
    cached = load_existing_cache()

    with open(CACHE_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

        for row in cached.values():
            writer.writerow(row)

        for entry in capitals:
            iso_code = entry["iso_code"]
            if iso_code in cached:
                continue
            try:
                solar, wind = fetch_climatology(float(entry["lat"]), float(entry["lon"]))
            except Exception as exc:
                print(f"SKIP {iso_code} ({entry['capital']}): {exc}")
                continue
            writer.writerow(
                {"iso_code": iso_code, "solar_kwh_per_m2_day": solar, "wind_speed_ms": wind}
            )
            f.flush()
            print(f"OK {iso_code} ({entry['capital']}): solar={solar} wind={wind}")
            time.sleep(0.2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_build_climatology_cache.py -v`
Expected: PASS

- [ ] **Step 6: Run the script for real**

Run: `python scripts/build_climatology_cache.py`
Expected: one `OK <iso_code> (<capital>): solar=... wind=...` line per country in `data/capitals.csv`, taking a few minutes (a 0.2s pause between requests, ~218 requests). A handful of `SKIP` lines (network hiccups) are acceptable — rerunning the script only retries what's missing, since it skips codes already in `data/power_climatology.csv`.

- [ ] **Step 7: Verify the cache file's coverage**

Run:
```bash
python -c "
import pandas as pd
capitals = pd.read_csv('data/capitals.csv')
cache = pd.read_csv('data/power_climatology.csv')
missing = set(capitals['iso_code']) - set(cache['iso_code'])
print(f'{len(cache)} / {len(capitals)} countries cached')
print('missing:', sorted(missing) if missing else 'none')
"
```
If any are missing, rerun Step 6 (it resumes) before proceeding. A small number of permanently-missing countries (e.g. a capital whose coordinates fall somewhere NASA POWER can't resolve) is an acceptable, documented gap per the spec's error-handling section — not a blocker.

- [ ] **Step 8: Run the full test suite**

Run: `pytest tests/ -v`
Expected: 13 passed.

- [ ] **Step 9: Commit**

```bash
git add scripts/ data/power_climatology.csv tests/test_build_climatology_cache.py
git commit -m "Add offline NASA POWER climatology fetch script and cache"
```

---

### Task 5: `data/climatology.py` — read the cache

**Files:**
- Create: `tests/test_climatology.py`, `data/climatology.py`
- Modify: `data/__init__.py`

**Interfaces:**
- Consumes: `data/power_climatology.csv` (Task 4), read by file path.
- Produces: `data.climatology.load_climatology_data(path=CLIMATOLOGY_PATH) -> pd.DataFrame` with columns `iso_code, solar_kwh_per_m2_day, wind_speed_ms`. `LoadedData` gains a field `climatology: pd.DataFrame`. Task 7 (`q4_charts.py`) and Task 9 (`pages/q4_renewables.py`) read `state.loaded.climatology`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_climatology.py
from data.climatology import load_climatology_data


def test_load_climatology_data_reads_iso_code_solar_and_wind_columns(tmp_path):
    csv_text = (
        "iso_code,solar_kwh_per_m2_day,wind_speed_ms\n"
        "USA,4.12,3.97\n"
        "ISL,2.05,6.31\n"
    )
    path = tmp_path / "power_climatology.csv"
    path.write_text(csv_text)

    result = load_climatology_data(str(path))

    assert list(result.columns) == ["iso_code", "solar_kwh_per_m2_day", "wind_speed_ms"]
    assert list(result["iso_code"]) == ["USA", "ISL"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_climatology.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'data.climatology'`

- [ ] **Step 3: Write `data/climatology.py`**

```python
"""Reads the NASA POWER solar/wind climatology cache — see
scripts/build_climatology_cache.py for how it's built. No network code
here or anywhere in the running app; this only reads a checked-in file.
"""

from pathlib import Path

import pandas as pd

CLIMATOLOGY_PATH = str(Path(__file__).resolve().parent / "power_climatology.csv")


def load_climatology_data(path: str = CLIMATOLOGY_PATH) -> pd.DataFrame:
    return pd.read_csv(path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_climatology.py -v`
Expected: PASS

- [ ] **Step 5: Extend `data/__init__.py`**

Add to imports:
```python
from .climatology import CLIMATOLOGY_PATH, load_climatology_data
```
Add `"CLIMATOLOGY_PATH", "load_climatology_data",` to `__all__`.

Change `LoadedData`:
```python
@dataclass
class LoadedData:
    co2_all: pd.DataFrame
    co2_countries: pd.DataFrame
    temperature: pd.DataFrame
    energy: pd.DataFrame
    climatology: pd.DataFrame
```

Change `load_all`:
```python
def load_all(
    co2_path: str = CO2_URL,
    gistemp_path: str = GISTEMP_URL,
    energy_path: str = ENERGY_URL,
    climatology_path: str = CLIMATOLOGY_PATH,
) -> LoadedData:
    """Load once at startup. Returns every frame the app needs."""
    co2_all = load_co2_data(co2_path)
    co2_countries = filter_countries(co2_all)
    temperature = load_temperature_data(gistemp_path)
    energy = load_energy_data(energy_path)
    climatology = load_climatology_data(climatology_path)
    return LoadedData(
        co2_all=co2_all,
        co2_countries=co2_countries,
        temperature=temperature,
        energy=energy,
        climatology=climatology,
    )
```

- [ ] **Step 6: Run the full test suite**

Run: `pytest tests/ -v`
Expected: 14 passed.

- [ ] **Step 7: Smoke-test app boot**

Run: `python app.py` in background, curl `http://127.0.0.1:8050/` (expect `200`), stop it. `load_all()` now reads the local climatology CSV too — confirm no error.

- [ ] **Step 8: Commit**

```bash
git add data/climatology.py data/__init__.py tests/test_climatology.py
git commit -m "Add data/climatology.py to read the cached NASA POWER data"
```

---

### Task 6: Q1 trend analysis helpers

**Files:**
- Create: `analysis.py`, `tests/test_analysis.py`

**Interfaces:**
- Consumes: nothing new (works on any frame shaped like `co2_all` filtered to `country == "World"`, i.e. columns `year`, `co2_growth_prct`).
- Produces: `analysis.rolling_growth_average(world_co2: pd.DataFrame, window: int = 5) -> pd.Series` (same index as `world_co2`); `analysis.growth_period_means(world_co2: pd.DataFrame, early_range: tuple, late_range: tuple) -> tuple[float, float]`. Task 9's `pages/q1_growth.py` calls both.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_analysis.py
import pandas as pd

from analysis import growth_period_means, rolling_growth_average


def test_rolling_growth_average_smooths_year_to_year_noise():
    world = pd.DataFrame({"year": [2000, 2001, 2002], "co2_growth_prct": [1.0, 3.0, 2.0]})

    result = rolling_growth_average(world, window=3)

    assert result.iloc[-1] == 2.0  # mean of 1.0, 3.0, 2.0


def test_growth_period_means_compares_two_year_ranges():
    world = pd.DataFrame(
        {
            "year": [1990, 1991, 2015, 2016],
            "co2_growth_prct": [2.0, 4.0, 1.0, 1.0],
        }
    )

    early, late = growth_period_means(world, (1990, 1991), (2015, 2016))

    assert early == 3.0
    assert late == 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_analysis.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'analysis'`

- [ ] **Step 3: Write `analysis.py`**

```python
"""Pure analytical helpers layered on top of the base charts in
prototype_charts.py. Kept separate and pure so they're unit-testable
without touching chart/plotting code.
"""

import pandas as pd


def rolling_growth_average(world_co2: pd.DataFrame, window: int = 5) -> pd.Series:
    """Rolling mean of co2_growth_prct, indexed the same as world_co2."""
    return world_co2["co2_growth_prct"].rolling(window=window, min_periods=1).mean()


def growth_period_means(world_co2: pd.DataFrame, early_range: tuple, late_range: tuple) -> tuple:
    """Mean growth rate over two year ranges, e.g. (1990, 1999) vs (2015, 2024)."""
    early = world_co2[world_co2["year"].between(*early_range)]["co2_growth_prct"].mean()
    late = world_co2[world_co2["year"].between(*late_range)]["co2_growth_prct"].mean()
    return early, late
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_analysis.py -v`
Expected: PASS

- [ ] **Step 5: Run the full test suite**

Run: `pytest tests/ -v`
Expected: 16 passed.

- [ ] **Step 6: Commit**

```bash
git add analysis.py tests/test_analysis.py
git commit -m "Add pure trend-analysis helpers for the Q1 page"
```

---

### Task 7: `q4_charts.py` — renewable potential vs adoption

**Files:**
- Create: `q4_charts.py`, `tests/test_q4_charts.py`

**Interfaces:**
- Consumes: `data.energy.RENEWABLE_SHARE_COLUMN`, `data.energy.renewable_share` (Task 2). Expects to be called with an already-filtered, single-year, country-level energy frame (columns include `iso_code`, `country`, `population`, `renewables_share_elec`) and a climatology frame (columns `iso_code`, `solar_kwh_per_m2_day`, `wind_speed_ms`) — same "caller filters, chart function assumes pre-filtered data" convention as `prototype_charts.py`.
- Produces: `q4_charts.trend_residuals(x: pd.Series, y: pd.Series) -> pd.Series`; `q4_charts.top_extremes(countries: pd.Series, residuals: pd.Series, n: int = 3) -> list`; `q4_charts.renewable_potential_vs_adoption_bubble(energy_df: pd.DataFrame, climatology_df: pd.DataFrame, potential: str = "solar") -> plotly Figure`. Task 9's `pages/q4_renewables.py` calls the bubble function; nothing else consumes the other two directly (they're tested standalone).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_q4_charts.py
import pandas as pd

from q4_charts import top_extremes, trend_residuals


def test_trend_residuals_is_zero_for_points_exactly_on_the_line():
    x = pd.Series([1.0, 2.0, 3.0])
    y = pd.Series([2.0, 4.0, 6.0])  # y = 2x, perfectly linear

    result = trend_residuals(x, y)

    assert all(abs(r) < 1e-9 for r in result)


def test_top_extremes_returns_furthest_above_and_below_the_trend():
    countries = pd.Series(["A", "B", "C", "D"])
    residuals = pd.Series([-10.0, 1.0, 2.0, 10.0])

    result = top_extremes(countries, residuals, n=1)

    assert result == ["A", "D"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_q4_charts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'q4_charts'`

- [ ] **Step 3: Write `q4_charts.py`**

```python
"""Q4 chart: renewable electricity adoption vs solar/wind potential."""

import numpy as np
import pandas as pd
import plotly.express as px

from data.energy import RENEWABLE_SHARE_COLUMN

POTENTIAL_COLUMNS = {
    "solar": "solar_kwh_per_m2_day",
    "wind": "wind_speed_ms",
}


def trend_residuals(x: pd.Series, y: pd.Series) -> pd.Series:
    """Vertical distance of each point from a best-fit line through (x, y)."""
    slope, intercept = np.polyfit(x, y, 1)
    predicted = slope * x + intercept
    return y - predicted


def top_extremes(countries: pd.Series, residuals: pd.Series, n: int = 3) -> list:
    """The n countries furthest below and furthest above the trend line, by name."""
    ranked = residuals.sort_values()
    below = list(countries.loc[ranked.index[:n]])
    above = list(countries.loc[ranked.index[-n:]])
    return below + above


def renewable_potential_vs_adoption_bubble(energy_df: pd.DataFrame, climatology_df: pd.DataFrame, potential: str = "solar"):
    """Bubble scatter: x = solar/wind potential, y = renewable electricity
    share, sized by population. The 3 countries furthest above and below a
    fitted trend line are labeled — the gap between natural potential and
    actual adoption is the point of this chart.
    """
    potential_col = POTENTIAL_COLUMNS[potential]
    merged = energy_df.merge(climatology_df, on="iso_code", how="inner")
    merged = merged.dropna(subset=[potential_col, RENEWABLE_SHARE_COLUMN, "population"])

    merged["residual"] = trend_residuals(merged[potential_col], merged[RENEWABLE_SHARE_COLUMN])
    labeled_countries = set(top_extremes(merged["country"], merged["residual"]))
    merged["label"] = merged["country"].where(merged["country"].isin(labeled_countries), "")

    fig = px.scatter(
        merged,
        x=potential_col,
        y=RENEWABLE_SHARE_COLUMN,
        size="population",
        text="label",
        hover_name="country",
        title=f"Renewable electricity share vs {potential} potential",
    )
    fig.update_traces(textposition="top center")
    fig.update_layout(
        xaxis_title=f"{potential.title()} potential ({'kWh/m2/day' if potential == 'solar' else 'm/s'})",
        yaxis_title="Renewable share of electricity (%)",
    )
    return fig
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_q4_charts.py -v`
Expected: PASS

- [ ] **Step 5: Verify the chart function against real data**

```bash
python -c "
import data
from data.co2 import filter_countries
import q4_charts

loaded = data.load_all()
energy_2023 = filter_countries(loaded.energy)
energy_2023 = energy_2023[energy_2023['year'] == 2023]
fig = q4_charts.renewable_potential_vs_adoption_bubble(energy_2023, loaded.climatology, potential='solar')
print('points:', len(fig.data[0].x))
print('labeled countries:', [t for t in fig.data[0].text if t])
fig_wind = q4_charts.renewable_potential_vs_adoption_bubble(energy_2023, loaded.climatology, potential='wind')
print('wind points:', len(fig_wind.data[0].x))
"
```
Expected: a non-trivial point count (well under 218, since it's the inner join of energy coverage × climatology cache coverage) and 6 labeled country names printed, different between solar and wind.

- [ ] **Step 6: Run the full test suite**

Run: `pytest tests/ -v`
Expected: 18 passed.

- [ ] **Step 7: Commit**

```bash
git add q4_charts.py tests/test_q4_charts.py
git commit -m "Add Q4 chart: renewable adoption vs solar/wind potential"
```

---

### Task 8: Multi-page shell — migrate Overview, Q1, Q2, Q3

**Files:**
- Create: `state.py`, `pages/overview.py`, `pages/q1_growth.py`, `pages/q2_emitters.py`, `pages/q3_gdp.py`
- Modify: `app.py` (full rewrite)
- Delete: nothing yet (Q4 page comes in Task 9)

**Interfaces:**
- Consumes: `data.load_all` (Tasks 1, 2, 5), `analysis.rolling_growth_average`/`growth_period_means` (Task 6), `prototype_charts.emissions_temperature_line`/`co2_growth_rate_bar`/`emissions_choropleth`/`top_emitters_paired_bar`/`gdp_emissions_bubble` (existing, untouched).
- Produces: `state.loaded` — a module-level `LoadedData` instance, loaded exactly once (Python caches module imports), importable as `import state; state.loaded.co2_all`. Task 9's `pages/q4_renewables.py` follows the same `import state` pattern.

This task has no new pure logic to TDD — it's wiring existing, already-tested chart functions into a new page structure. The test cycle here is "does each route return 200 and render its charts," verified via Dash's Flask test client (fast, no browser needed) plus one real-browser pass at the end.

- [ ] **Step 1: Write `state.py`**

```python
"""Frames loaded once at startup, shared by every page.

Importing this module triggers data.load_all() exactly once (Python
caches module imports) — every page imports `state` and reads
`state.loaded`, never calling data.load_all() itself.
"""

import data

loaded = data.load_all()
```

- [ ] **Step 2: Write `pages/overview.py`**

(No `pages/__init__.py` needed — Dash's `use_pages` discovers modules in the `pages_folder` directory by file scanning, not Python package import; confirmed by direct test against this Dash version before writing this plan.)

```python
"""Overview page: states all four research questions and headline numbers."""

import dash
from dash import html

import state

dash.register_page(__name__, path="/", name="Overview")


def layout():
    loaded = state.loaded
    latest_year = int(loaded.co2_countries["year"].max())
    world_latest = loaded.co2_all[
        (loaded.co2_all["country"] == "World") & (loaded.co2_all["year"] == latest_year)
    ].iloc[0]
    latest_temp = loaded.temperature.dropna(subset=["temperature_anomaly"]).iloc[-1]
    top_emitter = (
        loaded.co2_countries[loaded.co2_countries["year"] == latest_year]
        .nlargest(1, "co2")
        .iloc[0]
    )

    return html.Div([
        html.P("Four questions about CO2 emissions, warming, and the energy transition:"),
        html.Ul([
            html.Li("Q1 — Has global CO2 growth slowed since 2000?"),
            html.Li("Q2 — Who emits most in total, versus per person?"),
            html.Li("Q3 — Does higher GDP still mean higher emissions per person?"),
            html.Li("Q4 — Is renewable adoption tracking natural solar/wind potential?"),
        ]),
        html.H2("Headline numbers"),
        html.Ul([
            html.Li(f"Global CO2 emissions, {latest_year}: {world_latest['co2']:,.0f} Mt"),
            html.Li(
                f"Temperature anomaly, {int(latest_temp['year'])}: "
                f"{latest_temp['temperature_anomaly']:+.2f}°C vs 1951-1980"
            ),
            html.Li(f"Top emitter, {latest_year}: {top_emitter['country']} ({top_emitter['co2']:,.0f} Mt)"),
        ]),
    ])
```

- [ ] **Step 3: Write `pages/q1_growth.py`**

```python
"""Q1 page: has global CO2 growth slowed since 2000?"""

import dash
from dash import Input, Output, dcc, html

import analysis
import data
import prototype_charts as charts
import state

dash.register_page(__name__, path="/q1", name="Q1: Growth")

_MIN_YEAR = data.DEFAULT_YEAR_RANGE[0]
_MAX_YEAR = int(state.loaded.co2_countries["year"].max())


def layout():
    return html.Div([
        html.H2("Q1 — Has global CO2 growth slowed since 2000?"),
        html.Label("Year:", htmlFor="q1-year-slider"),
        dcc.Slider(
            id="q1-year-slider",
            min=_MIN_YEAR,
            max=_MAX_YEAR,
            step=1,
            value=_MAX_YEAR,
            marks={y: str(y) for y in range(_MIN_YEAR, _MAX_YEAR + 1, 5)},
            tooltip={"placement": "bottom", "always_visible": True},
        ),
        html.Div(
            style={"display": "flex", "gap": "20px", "flexWrap": "wrap"},
            children=[
                dcc.Graph(id="q1-line", style={"flex": "1", "minWidth": "450px"}),
                dcc.Graph(id="q1-growth-bar", style={"flex": "1", "minWidth": "450px"}),
            ],
        ),
    ])


@dash.callback(
    Output("q1-line", "figure"),
    Output("q1-growth-bar", "figure"),
    Input("q1-year-slider", "value"),
)
def update_q1(year):
    line_fig = charts.emissions_temperature_line(state.loaded.co2_all, state.loaded.temperature, year)
    bar_fig = charts.co2_growth_rate_bar(state.loaded.co2_all, year)

    world = state.loaded.co2_all[state.loaded.co2_all["country"] == "World"]
    world = world[world["year"] >= data.DEFAULT_YEAR_RANGE[0]]
    rolling = analysis.rolling_growth_average(world)
    bar_fig.add_scatter(x=world["year"], y=rolling, mode="lines", name="5-year rolling average")

    early, late = analysis.growth_period_means(world, (1990, 1999), (2015, 2024))
    bar_fig.add_annotation(
        xref="paper", yref="paper", x=0.02, y=0.98, showarrow=False, align="left",
        text=f"Mean growth 1990-1999: {early:.2f}%/yr<br>Mean growth 2015-2024: {late:.2f}%/yr",
        bgcolor="white", bordercolor="gray",
    )
    return line_fig, bar_fig
```

- [ ] **Step 4: Write `pages/q2_emitters.py`**

```python
"""Q2 page: who emits most in total, versus per person?"""

import io

import dash
from dash import Input, Output, dcc, html

import data
import prototype_charts as charts
import state

dash.register_page(__name__, path="/q2", name="Q2: Who Emits")

_MIN_YEAR = data.DEFAULT_YEAR_RANGE[0]
_MAX_YEAR = int(state.loaded.co2_countries["year"].max())
_COUNTRY_OPTIONS = sorted(state.loaded.co2_countries["country"].unique())


def layout():
    return html.Div([
        html.H2("Q2 — Who emits most in total, versus per person?"),
        html.Div(
            style={"display": "flex", "gap": "30px", "flexWrap": "wrap", "alignItems": "flex-end"},
            children=[
                html.Div(
                    style={"flex": "2", "minWidth": "300px"},
                    children=[
                        html.Label("Year:", htmlFor="q2-year-slider"),
                        dcc.Slider(
                            id="q2-year-slider", min=_MIN_YEAR, max=_MAX_YEAR, step=1, value=_MAX_YEAR,
                            marks={y: str(y) for y in range(_MIN_YEAR, _MAX_YEAR + 1, 5)},
                            tooltip={"placement": "bottom", "always_visible": True},
                        ),
                    ],
                ),
                html.Div(
                    style={"flex": "2", "minWidth": "250px"},
                    children=[
                        html.Label("Countries (optional filter):", htmlFor="q2-country-dropdown"),
                        dcc.Dropdown(
                            id="q2-country-dropdown",
                            options=[{"label": c, "value": c} for c in _COUNTRY_OPTIONS],
                            multi=True, placeholder="All countries",
                        ),
                    ],
                ),
                html.Div(
                    style={"flex": "1", "minWidth": "180px"},
                    children=[
                        html.Label("Map metric:", htmlFor="q2-metric-toggle"),
                        dcc.RadioItems(
                            id="q2-metric-toggle",
                            options=[
                                {"label": "Total", "value": "total"},
                                {"label": "Per capita", "value": "per_capita"},
                            ],
                            value="total", inline=True,
                        ),
                    ],
                ),
                html.Div([
                    html.Button("Download filtered CSV", id="q2-download-button"),
                    dcc.Download(id="q2-download-csv"),
                ]),
            ],
        ),
        dcc.Graph(id="q2-choropleth"),
        dcc.Graph(id="q2-paired-bar"),
    ])


def _filtered(selected_countries):
    countries = state.loaded.co2_countries
    if selected_countries:
        return countries[countries["country"].isin(selected_countries)]
    return countries


@dash.callback(
    Output("q2-choropleth", "figure"),
    Output("q2-paired-bar", "figure"),
    Input("q2-year-slider", "value"),
    Input("q2-country-dropdown", "value"),
    Input("q2-metric-toggle", "value"),
)
def update_q2(year, selected_countries, metric):
    countries = _filtered(selected_countries)
    return (
        charts.emissions_choropleth(countries, year, metric=metric),
        charts.top_emitters_paired_bar(countries, year),
    )


@dash.callback(
    Output("q2-download-csv", "data"),
    Input("q2-download-button", "n_clicks"),
    Input("q2-year-slider", "value"),
    Input("q2-country-dropdown", "value"),
    prevent_initial_call=True,
)
def download_q2(n_clicks, year, selected_countries):
    if dash.callback_context.triggered_id != "q2-download-button":
        raise dash.exceptions.PreventUpdate
    frame = _filtered(selected_countries)
    frame = frame[frame["year"] == year]
    buffer = io.StringIO()
    frame.to_csv(buffer, index=False)
    return dict(content=buffer.getvalue(), filename=f"q2_emitters_{year}.csv")
```

- [ ] **Step 5: Write `pages/q3_gdp.py`**

```python
"""Q3 page: does higher GDP still mean higher emissions per person?"""

import io

import dash
from dash import Input, Output, dcc, html

import data
import prototype_charts as charts
import state

dash.register_page(__name__, path="/q3", name="Q3: GDP")

_MIN_YEAR = data.DEFAULT_YEAR_RANGE[0]
_MAX_YEAR = int(state.loaded.co2_countries["year"].max())
_COUNTRY_OPTIONS = sorted(state.loaded.co2_countries["country"].unique())


def layout():
    return html.Div([
        html.H2("Q3 — Does higher GDP still mean higher emissions per person?"),
        html.Div(
            style={"display": "flex", "gap": "30px", "flexWrap": "wrap", "alignItems": "flex-end"},
            children=[
                html.Div(
                    style={"flex": "2", "minWidth": "300px"},
                    children=[
                        html.Label("Year:", htmlFor="q3-year-slider"),
                        dcc.Slider(
                            id="q3-year-slider", min=_MIN_YEAR, max=_MAX_YEAR, step=1, value=_MAX_YEAR,
                            marks={y: str(y) for y in range(_MIN_YEAR, _MAX_YEAR + 1, 5)},
                            tooltip={"placement": "bottom", "always_visible": True},
                        ),
                    ],
                ),
                html.Div(
                    style={"flex": "2", "minWidth": "250px"},
                    children=[
                        html.Label("Countries (optional filter):", htmlFor="q3-country-dropdown"),
                        dcc.Dropdown(
                            id="q3-country-dropdown",
                            options=[{"label": c, "value": c} for c in _COUNTRY_OPTIONS],
                            multi=True, placeholder="All countries",
                        ),
                    ],
                ),
                html.Div([
                    html.Button("Download filtered CSV", id="q3-download-button"),
                    dcc.Download(id="q3-download-csv"),
                ]),
            ],
        ),
        dcc.Graph(id="q3-bubble"),
    ])


def _filtered(selected_countries):
    countries = state.loaded.co2_countries
    if selected_countries:
        return countries[countries["country"].isin(selected_countries)]
    return countries


@dash.callback(
    Output("q3-bubble", "figure"),
    Input("q3-year-slider", "value"),
    Input("q3-country-dropdown", "value"),
)
def update_q3(year, selected_countries):
    return charts.gdp_emissions_bubble(_filtered(selected_countries), year)


@dash.callback(
    Output("q3-download-csv", "data"),
    Input("q3-download-button", "n_clicks"),
    Input("q3-year-slider", "value"),
    Input("q3-country-dropdown", "value"),
    prevent_initial_call=True,
)
def download_q3(n_clicks, year, selected_countries):
    if dash.callback_context.triggered_id != "q3-download-button":
        raise dash.exceptions.PreventUpdate
    frame = _filtered(selected_countries)
    frame = frame[frame["year"] == year]
    buffer = io.StringIO()
    frame.to_csv(buffer, index=False)
    return dict(content=buffer.getvalue(), filename=f"q3_gdp_{year}.csv")
```

- [ ] **Step 6: Rewrite `app.py` as the multi-page shell**

Replace the entire file with:

```python
"""Dash application shell for the Global Climate Trends dashboard.

Page layouts and callbacks live under pages/ (one module per question);
this file only builds the app object, top navigation, and footer. Data is
loaded once, in state.py, imported below before Dash scans pages/.
"""

import dash
from dash import html

import state  # noqa: F401 -- importing triggers data.load_all() once

app = dash.Dash(__name__, use_pages=True)
app.title = "Global Climate Trends"
server = app.server  # gunicorn entry point: app:server

app.layout = html.Div(
    style={"fontFamily": "Arial, sans-serif", "maxWidth": "1100px", "margin": "0 auto", "padding": "20px"},
    children=[
        html.H1("Global Climate Trends"),
        html.Nav(
            style={
                "display": "flex", "gap": "15px", "marginBottom": "20px",
                "borderBottom": "1px solid #ddd", "paddingBottom": "10px",
            },
            children=[
                html.A(page["name"], href=page["relative_path"])
                for page in dash.page_registry.values()
            ],
        ),
        dash.page_container,
        html.Footer(
            style={
                "marginTop": "40px", "fontSize": "0.85em", "color": "#555",
                "borderTop": "1px solid #ddd", "paddingTop": "10px",
            },
            children=[
                html.P([
                    "CO2, GDP, and energy data: Our World in Data, ",
                    html.A("co2-data", href="https://github.com/owid/co2-data", target="_blank"),
                    " and ",
                    html.A("energy-data", href="https://github.com/owid/energy-data", target="_blank"),
                    " (CC BY 4.0). ",
                ]),
                html.P([
                    "Temperature data: NASA GISS, ",
                    html.A("GISTEMP v4", href="https://data.giss.nasa.gov/gistemp/", target="_blank"),
                    " (public domain). Solar/wind climatology: NASA ",
                    html.A("POWER", href="https://power.larc.nasa.gov/", target="_blank"),
                    " (public domain).",
                ]),
            ],
        ),
    ],
)

if __name__ == "__main__":
    app.run(debug=True)
```

- [ ] **Step 7: Verify every route responds, via the Flask test client**

```bash
python -c "
import app as appmod
client = appmod.app.server.test_client()
for path in ['/', '/q1', '/q2', '/q3']:
    r = client.get(path)
    print(path, r.status_code)
"
```
Expected: `200` for all four paths.

- [ ] **Step 8: Run the full test suite**

Run: `pytest tests/ -v`
Expected: 18 passed (no new tests in this task — this is wiring, verified via the test-client check above and the browser check below, matching how the original single-page `app.py` was verified).

- [ ] **Step 9: Browser check**

Start the app (`python app.py`), open `http://127.0.0.1:8050/` in a browser, click through Overview, Q1, Q2, Q3 in the nav, move each page's year slider, and confirm charts update and (on Q2/Q3) the CSV download button produces a file. Check the browser console for errors. Stop the server.

- [ ] **Step 10: Commit**

```bash
git add state.py pages/ app.py
git commit -m "Restructure app.py into a multi-page shell (Overview, Q1, Q2, Q3)"
```

---

### Task 9: Q4 page

**Files:**
- Create: `pages/q4_renewables.py`

**Interfaces:**
- Consumes: `q4_charts.renewable_potential_vs_adoption_bubble` (Task 7), `state.loaded.energy`/`state.loaded.climatology` (Tasks 2, 5, 8), `data.filter_countries` (Task 1), `data.energy.ENERGY_MAX_YEAR` (Task 2).
- Produces: the `/q4` route, automatically picked up by `app.py`'s nav loop (Task 8 iterates `dash.page_registry.values()`, so no `app.py` change is needed here).

- [ ] **Step 1: Write `pages/q4_renewables.py`**

```python
"""Q4 page: is renewable adoption tracking natural solar/wind potential?"""

import io

import dash
from dash import Input, Output, dcc, html

import data
import q4_charts
import state
from data.energy import ENERGY_MAX_YEAR

dash.register_page(__name__, path="/q4", name="Q4: Renewables")

_MIN_YEAR = data.DEFAULT_YEAR_RANGE[0]
_MAX_YEAR = ENERGY_MAX_YEAR


def layout():
    return html.Div([
        html.H2("Q4 — Is renewable adoption tracking natural solar/wind potential?"),
        html.Div(
            style={"display": "flex", "gap": "30px", "flexWrap": "wrap", "alignItems": "flex-end"},
            children=[
                html.Div(
                    style={"flex": "2", "minWidth": "300px"},
                    children=[
                        html.Label("Year:", htmlFor="q4-year-slider"),
                        dcc.Slider(
                            id="q4-year-slider", min=_MIN_YEAR, max=_MAX_YEAR, step=1, value=_MAX_YEAR,
                            marks={y: str(y) for y in range(_MIN_YEAR, _MAX_YEAR + 1, 5)},
                            tooltip={"placement": "bottom", "always_visible": True},
                        ),
                    ],
                ),
                html.Div(
                    style={"flex": "1", "minWidth": "180px"},
                    children=[
                        html.Label("Potential:", htmlFor="q4-potential-toggle"),
                        dcc.RadioItems(
                            id="q4-potential-toggle",
                            options=[
                                {"label": "Solar", "value": "solar"},
                                {"label": "Wind", "value": "wind"},
                            ],
                            value="solar", inline=True,
                        ),
                    ],
                ),
                html.Div([
                    html.Button("Download filtered CSV", id="q4-download-button"),
                    dcc.Download(id="q4-download-csv"),
                ]),
            ],
        ),
        dcc.Graph(id="q4-bubble"),
    ])


def _energy_for_year(year):
    energy_countries = data.filter_countries(state.loaded.energy)
    return energy_countries[energy_countries["year"] == year]


@dash.callback(
    Output("q4-bubble", "figure"),
    Input("q4-year-slider", "value"),
    Input("q4-potential-toggle", "value"),
)
def update_q4(year, potential):
    energy_year = _energy_for_year(year)
    return q4_charts.renewable_potential_vs_adoption_bubble(
        energy_year, state.loaded.climatology, potential=potential
    )


@dash.callback(
    Output("q4-download-csv", "data"),
    Input("q4-download-button", "n_clicks"),
    Input("q4-year-slider", "value"),
    Input("q4-potential-toggle", "value"),
    prevent_initial_call=True,
)
def download_q4(n_clicks, year, potential):
    if dash.callback_context.triggered_id != "q4-download-button":
        raise dash.exceptions.PreventUpdate
    energy_year = _energy_for_year(year)
    merged = energy_year.merge(state.loaded.climatology, on="iso_code", how="inner")
    buffer = io.StringIO()
    merged.to_csv(buffer, index=False)
    return dict(content=buffer.getvalue(), filename=f"q4_renewables_{year}.csv")
```

- [ ] **Step 2: Verify the route responds**

```bash
python -c "
import app as appmod
client = appmod.app.server.test_client()
r = client.get('/q4')
print('/q4', r.status_code)
"
```
Expected: `200`

- [ ] **Step 3: Run the full test suite**

Run: `pytest tests/ -v`
Expected: 18 passed (unchanged — this task is wiring, same rationale as Task 8).

- [ ] **Step 4: Browser check**

Start the app, open `/q4`, confirm the bubble chart renders, the Solar/Wind toggle changes the x-axis, the year slider updates the chart, and the CSV download works. Check the browser console for errors. Stop the server.

- [ ] **Step 5: Commit**

```bash
git add pages/q4_renewables.py
git commit -m "Add Q4 page: renewable adoption vs solar/wind potential"
```

---

### Task 10: Docs and final verification

**Files:**
- Modify: `CLAUDE.md`, `README.md`

**Interfaces:**
- Consumes: nothing new — this task only updates documentation to match Tasks 1-9's final state.
- Produces: nothing consumed by other tasks (this is the last task).

- [ ] **Step 1: Update `CLAUDE.md`'s "Current state" table**

Add rows for the new files (`data/energy.py`, `data/climatology.py`, `data/capitals.csv`, `scripts/build_climatology_cache.py`, `analysis.py`, `q4_charts.py`, `state.py`, `pages/*.py`) and note the multi-page restructuring, mirroring the style already used for the Week 4 entries.

- [ ] **Step 2: Update `README.md`'s file table and run instructions**

Reflect the `data/` package split, the new `pages/` structure, and the one-time `scripts/build_climatology_cache.py` step (only needed if `data/power_climatology.csv` is regenerated — not needed for a normal `pip install && python app.py` run, since the cache file is committed).

- [ ] **Step 3: Full test suite**

Run: `pytest tests/ -v`
Expected: 18 passed, 0 warnings.

- [ ] **Step 4: Full browser walkthrough**

Start the app, visit Overview, Q1, Q2, Q3, Q4 in a browser. For each page: confirm charts render with real data, exercise every control (sliders, dropdowns, toggles), confirm CSV downloads on Q2/Q3/Q4, check the browser console for errors on each page. Stop the server.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "Update docs for the expanded 4-question multi-page dashboard"
```
