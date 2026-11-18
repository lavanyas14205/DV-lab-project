# Priority 1 Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the three Priority 1 features from the enhancement backlog — Country Climate Profile, Compare Years, and Q4 outlier callouts — to the existing multi-page Dash dashboard, without restructuring what already works.

**Architecture:** Two new routed pages (`/country`, `/compare`) plus one modification to the existing `/q4` page. All three reuse the existing `data/` loaders via `state.loaded` (loaded once at startup) and a small set of new generic, pure helper functions added to `analysis.py`. No new datasets, no new dependencies, no changes to `data/` cleaning logic.

**Tech Stack:** Python, Pandas, Plotly, Dash (`dash.register_page`, `@dash.callback`), pytest.

**Spec:** `docs/PROJECT_REPORT.md` §11 ("Planned enhancements (next phase)") — the three "Committed for the next phase" items. `CLAUDE.md` for the cleaning rules referenced below.

## Global Constraints

- Rule 2 (from `CLAUDE.md`): GDP charts/values must be capped at `data.co2.GDP_MAX_YEAR` (2022) — never extrapolate.
- Rule 4: default year-range start is `data.DEFAULT_YEAR_RANGE[0]` (1990).
- Rule 6: per-capita rankings exclude countries under `data.co2.MIN_POPULATION_FOR_PER_CAPITA` — not applicable to these three features (none rank countries by per-capita value), so no change needed here.
- Rule 7: renewable-adoption values must use `data.energy.RENEWABLE_SHARE_COLUMN` (`renewables_share_elec`), capped at `data.energy.ENERGY_MAX_YEAR` (2023).
- Never `fillna(0)` on missing values anywhere — a missing measurement must render as "n/a" / be skipped, never as a plotted zero.
- Q4 outlier callouts must not claim causation — "above/below the fitted trend" only, per `docs/PROJECT_REPORT.md` §11's explicit non-causal requirement.
- No new pip dependencies — `requirements.txt` stays as-is (pandas, plotly, dash, gunicorn).
- Keep code commented only where non-obvious (matches existing style in `analysis.py`, `q4_charts.py`); this is graded coursework explained in a viva.
- Every new pure function goes in `analysis.py` or a `*_charts.py` module (matching the existing split: cleaning in `data/`, pure numeric helpers in `analysis.py`, chart construction in `*_charts.py`, interactivity in `pages/*.py`) and gets a pytest test alongside the existing tests in `tests/`.

---

## File Structure

- **Modify:** `analysis.py` — add `country_series`, `latest_value`, `with_gdp_per_capita`, `value_at_year`, `percent_change`, `absolute_change`.
- **Modify:** `tests/test_analysis.py` — tests for the six new functions.
- **Create:** `country_profile_charts.py` — `country_trend_sparklines()`.
- **Create:** `tests/test_country_profile_charts.py` — test for `country_trend_sparklines()`.
- **Create:** `pages/country_profile.py` — the `/country` page (layout + callback).
- **Create:** `pages/compare_years.py` — the `/compare` page (layout + callback).
- **Modify:** `q4_charts.py` — extract shared `_prepare()`, add `POTENTIAL_UNITS` and `outlier_details()`.
- **Modify:** `tests/test_q4_charts.py` — test for `outlier_details()`.
- **Modify:** `pages/q4_renewables.py` — render the Adoption Leaders / Potential Under-Utilisers callouts.
- **Modify:** `docs/PROJECT_REPORT.md`, `CLAUDE.md` — record the three features as shipped, add new files to the file-layout tables.

No changes to `app.py` — new pages register their own route via `dash.register_page`, and the nav bar is already built from `dash.page_registry` (see `app.py:26-29`), so `/country` and `/compare` appear automatically.

---

### Task 1: `analysis.py` — `country_series` and `latest_value`

**Files:**
- Modify: `analysis.py`
- Test: `tests/test_analysis.py`

**Interfaces:**
- Produces: `country_series(df: pd.DataFrame, country: str, value_column: str, min_year: int | None = None, max_year: int | None = None) -> pd.DataFrame` — returns a frame with exactly columns `["year", "value"]`, sorted by year ascending, with rows where `value_column` is NaN dropped, optionally bounded to `[min_year, max_year]`.
- Produces: `latest_value(series: pd.DataFrame) -> tuple[int, float] | None` — takes a `country_series()`-shaped frame (columns `year`, `value`) and returns `(year, value)` of its last row, or `None` if the frame is empty.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_analysis.py`:

```python
from analysis import country_series, latest_value


def test_country_series_drops_nan_and_sorts_by_year():
    df = pd.DataFrame(
        {
            "country": ["India", "India", "India", "China"],
            "year": [2002, 2000, 2001, 2000],
            "co2": [5.0, 3.0, None, 9.0],
        }
    )

    result = country_series(df, "India", "co2")

    assert list(result["year"]) == [2000]
    assert list(result["value"]) == [3.0]


def test_country_series_respects_min_and_max_year():
    df = pd.DataFrame(
        {"country": ["India"] * 4, "year": [1989, 1990, 2000, 2023], "co2": [1.0, 2.0, 3.0, 4.0]}
    )

    result = country_series(df, "India", "co2", min_year=1990, max_year=2000)

    assert list(result["year"]) == [1990, 2000]


def test_latest_value_returns_last_row_as_year_value_tuple():
    series = pd.DataFrame({"year": [2000, 2001, 2002], "value": [1.0, 2.0, 3.0]})

    result = latest_value(series)

    assert result == (2002, 3.0)


def test_latest_value_returns_none_for_empty_series():
    series = pd.DataFrame({"year": [], "value": []})

    assert latest_value(series) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_analysis.py -v`
Expected: FAIL with `ImportError: cannot import name 'country_series'` (and `latest_value`).

- [ ] **Step 3: Implement in `analysis.py`**

Add to `analysis.py` (after the existing `growth_period_means` function):

```python
def country_series(
    df: pd.DataFrame,
    country: str,
    value_column: str,
    min_year: int | None = None,
    max_year: int | None = None,
) -> pd.DataFrame:
    """One country's (year, value) trend for one column, NaNs dropped.

    Bounds are optional — e.g. GDP capped at data.co2.GDP_MAX_YEAR (rule 2),
    or the dashboard's default 1990 start (rule 4). Always returns exactly
    ["year", "value"] columns so callers don't need to know the source
    column name.
    """
    frame = df[df["country"] == country].dropna(subset=[value_column])
    if min_year is not None:
        frame = frame[frame["year"] >= min_year]
    if max_year is not None:
        frame = frame[frame["year"] <= max_year]
    frame = frame.sort_values("year")
    return frame[["year", value_column]].rename(columns={value_column: "value"})


def latest_value(series: pd.DataFrame) -> tuple | None:
    """(year, value) of the last row of a country_series() result, or None."""
    if series.empty:
        return None
    row = series.iloc[-1]
    return int(row["year"]), float(row["value"])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_analysis.py -v`
Expected: PASS (all tests in the file, old and new).

- [ ] **Step 5: Commit**

```bash
git add analysis.py tests/test_analysis.py
git commit -m "$(cat <<'EOF'
Add country_series/latest_value helpers for per-country trend lookups

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `analysis.py` — `with_gdp_per_capita`

**Files:**
- Modify: `analysis.py`
- Test: `tests/test_analysis.py`

**Interfaces:**
- Consumes: none new (plain `pd.DataFrame` with `gdp` and `population` columns, as in `state.loaded.co2_countries`).
- Produces: `with_gdp_per_capita(co2_countries: pd.DataFrame) -> pd.DataFrame` — returns a copy of the input with an added `gdp_per_capita` column (`gdp / population`, `NaN` where either is missing). The result feeds `country_series(..., "gdp_per_capita", ...)` in Task 5.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_analysis.py`:

```python
from analysis import with_gdp_per_capita


def test_with_gdp_per_capita_adds_derived_column():
    df = pd.DataFrame({"country": ["India", "Palau"], "gdp": [3_000_000, None], "population": [1_400_000_000, 18_000]})

    result = with_gdp_per_capita(df)

    assert result.loc[0, "gdp_per_capita"] == 3_000_000 / 1_400_000_000
    assert pd.isna(result.loc[1, "gdp_per_capita"])
    assert "gdp" in df.columns  # original frame untouched
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_analysis.py::test_with_gdp_per_capita_adds_derived_column -v`
Expected: FAIL with `ImportError: cannot import name 'with_gdp_per_capita'`.

- [ ] **Step 3: Implement in `analysis.py`**

Add to `analysis.py`:

```python
def with_gdp_per_capita(co2_countries: pd.DataFrame) -> pd.DataFrame:
    """co2_countries plus a derived gdp_per_capita column.

    NaN where gdp or population is missing — never filled with 0 (a missing
    GDP is not a zero GDP). Same derivation prototype_charts.gdp_emissions_bubble
    uses inline; factored out here so it's reusable and testable on its own.
    """
    out = co2_countries.copy()
    out["gdp_per_capita"] = out["gdp"] / out["population"]
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_analysis.py -v`
Expected: PASS (all tests in the file).

- [ ] **Step 5: Commit**

```bash
git add analysis.py tests/test_analysis.py
git commit -m "$(cat <<'EOF'
Add with_gdp_per_capita helper for the Country Profile page

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `analysis.py` — `value_at_year`, `percent_change`, `absolute_change`

**Files:**
- Modify: `analysis.py`
- Test: `tests/test_analysis.py`

**Interfaces:**
- Produces: `value_at_year(df: pd.DataFrame, year: int, column: str) -> float | None` — value of `column` at `year` in a single-row-per-year frame (e.g. the "World" rows of `co2_all`/`energy`, or `state.loaded.temperature`), or `None` if that year is absent or the value is `NaN`.
- Produces: `percent_change(from_value: float | None, to_value: float | None) -> float | None` — `(to - from) / from * 100`, or `None` if either input is `None` or `from_value == 0`.
- Produces: `absolute_change(from_value: float | None, to_value: float | None) -> float | None` — `to - from`, or `None` if either input is `None`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_analysis.py`:

```python
from analysis import absolute_change, percent_change, value_at_year


def test_value_at_year_returns_the_matching_row_value():
    df = pd.DataFrame({"year": [2020, 2021], "co2": [100.0, 110.0]})

    assert value_at_year(df, 2021, "co2") == 110.0


def test_value_at_year_returns_none_when_year_missing():
    df = pd.DataFrame({"year": [2020], "co2": [100.0]})

    assert value_at_year(df, 1999, "co2") is None


def test_value_at_year_returns_none_when_value_is_nan():
    df = pd.DataFrame({"year": [2020], "co2": [None]})

    assert value_at_year(df, 2020, "co2") is None


def test_percent_change_computes_relative_change():
    assert percent_change(100.0, 150.0) == 50.0


def test_percent_change_returns_none_for_missing_or_zero_baseline():
    assert percent_change(None, 150.0) is None
    assert percent_change(0.0, 150.0) is None


def test_absolute_change_computes_difference():
    assert absolute_change(1.0, 1.3) == pytest.approx(0.3)


def test_absolute_change_returns_none_when_either_value_missing():
    assert absolute_change(None, 1.3) is None
```

This test file needs `pytest` imported for `pytest.approx` — add `import pytest` to the top of `tests/test_analysis.py` alongside the existing `import pandas as pd`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_analysis.py -v`
Expected: FAIL with `ImportError: cannot import name 'value_at_year'`.

- [ ] **Step 3: Implement in `analysis.py`**

Add to `analysis.py`:

```python
def value_at_year(df: pd.DataFrame, year: int, column: str) -> float | None:
    """Value of `column` at `year` in a single-row-per-year frame.

    Used for global aggregates (the "World" row of co2_all/energy, or
    state.loaded.temperature, which has no country dimension at all).
    Returns None rather than a fabricated 0 when the year is missing or the
    value is NaN.
    """
    matches = df[df["year"] == year]
    if matches.empty:
        return None
    value = matches.iloc[0][column]
    return None if pd.isna(value) else float(value)


def percent_change(from_value: float | None, to_value: float | None) -> float | None:
    """(to - from) / from * 100. None if either value or the baseline is missing/zero."""
    if from_value is None or to_value is None or from_value == 0:
        return None
    return (to_value - from_value) / from_value * 100


def absolute_change(from_value: float | None, to_value: float | None) -> float | None:
    """to - from. None if either value is missing (e.g. temperature anomaly,
    where a percent change is meaningless near a zero baseline)."""
    if from_value is None or to_value is None:
        return None
    return to_value - from_value
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_analysis.py -v`
Expected: PASS (all tests in the file).

- [ ] **Step 5: Commit**

```bash
git add analysis.py tests/test_analysis.py
git commit -m "$(cat <<'EOF'
Add value_at_year/percent_change/absolute_change helpers for Compare Years

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: `country_profile_charts.py` — trend sparklines

**Files:**
- Create: `country_profile_charts.py`
- Test: `tests/test_country_profile_charts.py`

**Interfaces:**
- Consumes: a `dict[str, pd.DataFrame]` mapping a display label to a `country_series()`-shaped frame (columns `year`, `value`) — produced by Task 1's `country_series()`.
- Produces: `country_trend_sparklines(series_by_label: dict) -> go.Figure` — one small line-chart subplot per non-empty entry in `series_by_label`, in the order given.

- [ ] **Step 1: Write the failing test**

Create `tests/test_country_profile_charts.py`:

```python
import pandas as pd

from country_profile_charts import country_trend_sparklines


def test_country_trend_sparklines_makes_one_subplot_per_nonempty_series():
    series_by_label = {
        "CO2 (Mt)": pd.DataFrame({"year": [2000, 2001], "value": [1.0, 2.0]}),
        "GDP/person ($)": pd.DataFrame({"year": [], "value": []}),  # e.g. a country with no GDP data
        "Renewables (%)": pd.DataFrame({"year": [2000, 2001], "value": [10.0, 12.0]}),
    }

    fig = country_trend_sparklines(series_by_label)

    subplot_titles = [ann["text"] for ann in fig.layout.annotations]
    assert subplot_titles == ["CO2 (Mt)", "Renewables (%)"]
    assert len(fig.data) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_country_profile_charts.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'country_profile_charts'`.

- [ ] **Step 3: Implement `country_profile_charts.py`**

Create `country_profile_charts.py`:

```python
"""Chart builder for the Country Climate Profile page (pages/country_profile.py)."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots


def country_trend_sparklines(series_by_label: dict) -> go.Figure:
    """One small line chart per non-empty {label: DataFrame[year, value]} entry.

    A country missing one metric entirely (e.g. no GDP data) just gets fewer
    subplots rather than an empty/broken one.
    """
    items = [(label, series) for label, series in series_by_label.items() if not series.empty]
    fig = make_subplots(rows=1, cols=len(items), subplot_titles=[label for label, _ in items])
    for i, (_, series) in enumerate(items, start=1):
        fig.add_trace(
            go.Scatter(x=series["year"], y=series["value"], mode="lines", showlegend=False),
            row=1, col=i,
        )
    fig.update_layout(height=300, margin=dict(t=60, b=30), title="Trend, 1990-present")
    return fig
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_country_profile_charts.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add country_profile_charts.py tests/test_country_profile_charts.py
git commit -m "$(cat <<'EOF'
Add country_trend_sparklines chart builder for Country Climate Profile

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `pages/country_profile.py` — the Country Climate Profile page

**Files:**
- Create: `pages/country_profile.py`

**Interfaces:**
- Consumes: `analysis.country_series`, `analysis.latest_value`, `analysis.with_gdp_per_capita` (Tasks 1-2); `country_profile_charts.country_trend_sparklines` (Task 4); `state.loaded` (`co2_countries`, `energy`); `data.DEFAULT_YEAR_RANGE`; `data.co2.GDP_MAX_YEAR`; `data.energy.ENERGY_MAX_YEAR`, `data.energy.RENEWABLE_SHARE_COLUMN`.
- Produces: registers Dash route `/country`, named "Country Profile" — picked up automatically by `app.py`'s nav (`dash.page_registry`).

This is a Dash page, following the exact structure of `pages/q3_gdp.py` (dropdown + callback, no download button needed here). No dedicated unit test — Dash pages in this codebase are verified by booting the app (Task 6), matching the existing convention (none of `pages/q1_growth.py`, `q2_emitters.py`, `q3_gdp.py`, `q4_renewables.py` have a test file).

- [ ] **Step 1: Create `pages/country_profile.py`**

```python
"""Country Climate Profile page: one country's headline numbers and trends."""

import dash
from dash import Input, Output, dcc, html

import analysis
import country_profile_charts as charts
import data
import state
from data.co2 import GDP_MAX_YEAR
from data.energy import ENERGY_MAX_YEAR, RENEWABLE_SHARE_COLUMN

dash.register_page(__name__, path="/country", name="Country Profile")

_COUNTRY_OPTIONS = sorted(state.loaded.co2_countries["country"].unique())
_LATEST_YEAR = int(state.loaded.co2_countries["year"].max())
_DEFAULT_COUNTRY = (
    state.loaded.co2_countries[state.loaded.co2_countries["year"] == _LATEST_YEAR]
    .nlargest(1, "co2")
    .iloc[0]["country"]
)


def layout():
    return html.Div([
        html.H2("Country Climate Profile"),
        html.Label("Country:", htmlFor="country-profile-dropdown"),
        dcc.Dropdown(
            id="country-profile-dropdown",
            options=[{"label": c, "value": c} for c in _COUNTRY_OPTIONS],
            value=_DEFAULT_COUNTRY,
            clearable=False,
        ),
        html.Div(
            id="country-profile-kpis",
            style={"display": "flex", "gap": "30px", "flexWrap": "wrap", "margin": "20px 0"},
        ),
        dcc.Graph(id="country-profile-trends"),
    ])


def _kpi_card(label, value_text):
    return html.Div(
        style={"minWidth": "160px"},
        children=[
            html.Div(label, style={"fontSize": "0.8em", "color": "#666"}),
            html.Div(value_text, style={"fontSize": "1.4em"}),
        ],
    )


@dash.callback(
    Output("country-profile-kpis", "children"),
    Output("country-profile-trends", "figure"),
    Input("country-profile-dropdown", "value"),
)
def update_country_profile(country):
    co2_gdp = analysis.with_gdp_per_capita(state.loaded.co2_countries)
    min_year = data.DEFAULT_YEAR_RANGE[0]

    population_series = analysis.country_series(state.loaded.co2_countries, country, "population")
    co2_series = analysis.country_series(state.loaded.co2_countries, country, "co2", min_year=min_year)
    co2_pc_series = analysis.country_series(
        state.loaded.co2_countries, country, "co2_per_capita", min_year=min_year
    )
    gdp_pc_series = analysis.country_series(
        co2_gdp, country, "gdp_per_capita", min_year=min_year, max_year=GDP_MAX_YEAR
    )
    renew_series = analysis.country_series(
        state.loaded.energy, country, RENEWABLE_SHARE_COLUMN, min_year=min_year, max_year=ENERGY_MAX_YEAR
    )

    kpis = []
    pop_latest = analysis.latest_value(population_series)
    kpis.append(_kpi_card("Population", f"{pop_latest[1]:,.0f}" if pop_latest else "No data"))
    gdp_latest = analysis.latest_value(gdp_pc_series)
    kpis.append(
        _kpi_card("GDP / person", f"${gdp_latest[1]:,.0f} ({gdp_latest[0]})" if gdp_latest else "No data")
    )
    co2_latest = analysis.latest_value(co2_series)
    kpis.append(
        _kpi_card("CO2 emissions", f"{co2_latest[1]:,.0f} Mt ({co2_latest[0]})" if co2_latest else "No data")
    )
    co2_pc_latest = analysis.latest_value(co2_pc_series)
    kpis.append(
        _kpi_card("CO2 / person", f"{co2_pc_latest[1]:.1f} t ({co2_pc_latest[0]})" if co2_pc_latest else "No data")
    )
    renew_latest = analysis.latest_value(renew_series)
    kpis.append(
        _kpi_card(
            "Renewable electricity",
            f"{renew_latest[1]:.0f}% ({renew_latest[0]})" if renew_latest else "No data",
        )
    )

    fig = charts.country_trend_sparklines({
        "CO2 emissions (Mt)": co2_series,
        "CO2 per person (t)": co2_pc_series,
        "GDP per person ($)": gdp_pc_series,
        "Renewable electricity (%)": renew_series,
    })
    return kpis, fig
```

- [ ] **Step 2: Commit**

```bash
git add pages/country_profile.py
git commit -m "$(cat <<'EOF'
Add Country Climate Profile page (/country)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Manual verification — Country Climate Profile

**Files:** none (verification only).

- [ ] **Step 1: Boot the app**

Run: `python app.py` (leave running)

- [ ] **Step 2: Check the page loads with real data**

Open `http://127.0.0.1:8050/country` in a browser (or `curl -s http://127.0.0.1:8050/country | grep -o "<title>[^<]*</title>"` to confirm a 200/non-error response — the page content itself is rendered client-side by Dash, so a full check needs a browser).

In the browser: confirm the country dropdown defaults to the current top emitter, five KPI cards show non-"No data" numbers, and the trend chart shows up to four line subplots. Switch the dropdown to a small country (e.g. Palau or another nation likely missing GDP/renewables coverage) and confirm the KPI cards show "No data" gracefully (no crash, no `NaN` printed) and the trend chart simply shows fewer subplots.

- [ ] **Step 3: Stop the app**

Find and kill the `python app.py` process (or its listener on port 8050) before moving on.

---

### Task 7: `pages/compare_years.py` — the Compare Years page

**Files:**
- Create: `pages/compare_years.py`

**Interfaces:**
- Consumes: `analysis.value_at_year`, `analysis.percent_change`, `analysis.absolute_change` (Task 3); `state.loaded` (`co2_all`, `energy`, `temperature`); `data.DEFAULT_YEAR_RANGE`.
- Produces: registers Dash route `/compare`, named "Compare Years".

- [ ] **Step 1: Create `pages/compare_years.py`**

```python
"""Compare Years page: global metrics at two chosen years, side by side."""

import dash
from dash import Input, Output, dcc, html

import analysis
import data
import state

dash.register_page(__name__, path="/compare", name="Compare Years")

_MIN_YEAR = data.DEFAULT_YEAR_RANGE[0]
_MAX_YEAR = int(state.loaded.co2_countries["year"].max())

# "World" aggregate rows carry the global totals used here — the same rows
# prototype_charts.emissions_temperature_line uses for the Q1 line chart.
_WORLD_CO2 = state.loaded.co2_all[state.loaded.co2_all["country"] == "World"]
_WORLD_ENERGY = state.loaded.energy[state.loaded.energy["country"] == "World"]
_TEMPERATURE = state.loaded.temperature

# (label, frame, column, change type). "absolute" is used for temperature
# anomaly, where a percent change is meaningless near a near-zero baseline.
_ROWS = [
    ("Global CO2 emissions (Mt)", _WORLD_CO2, "co2", "percent"),
    ("CO2 per person (t)", _WORLD_CO2, "co2_per_capita", "percent"),
    ("Renewable electricity share (%)", _WORLD_ENERGY, "renewables_share_elec", "percent"),
    ("Temperature anomaly (°C)", _TEMPERATURE, "temperature_anomaly", "absolute"),
]


def layout():
    years = list(range(_MIN_YEAR, _MAX_YEAR + 1))
    year_options = [{"label": str(y), "value": y} for y in years]
    return html.Div([
        html.H2("Compare Years"),
        html.P("Pick two years to see how the global picture changed between them."),
        html.Div(
            style={"display": "flex", "gap": "20px", "alignItems": "flex-end"},
            children=[
                html.Div([
                    html.Label("From year:", htmlFor="compare-year-from"),
                    dcc.Dropdown(
                        id="compare-year-from", options=year_options, value=_MIN_YEAR, clearable=False
                    ),
                ]),
                html.Div([
                    html.Label("To year:", htmlFor="compare-year-to"),
                    dcc.Dropdown(
                        id="compare-year-to", options=year_options, value=_MAX_YEAR, clearable=False
                    ),
                ]),
            ],
        ),
        html.Div(id="compare-years-table", style={"marginTop": "20px"}),
    ])


def _format_value(value):
    return f"{value:,.2f}" if value is not None else "n/a"


@dash.callback(
    Output("compare-years-table", "children"),
    Input("compare-year-from", "value"),
    Input("compare-year-to", "value"),
)
def update_compare_years(year_from, year_to):
    rows = []
    for label, frame, column, change_type in _ROWS:
        from_value = analysis.value_at_year(frame, year_from, column)
        to_value = analysis.value_at_year(frame, year_to, column)
        if change_type == "percent":
            change = analysis.percent_change(from_value, to_value)
            change_text = f"{change:+.1f}%" if change is not None else "n/a"
        else:
            change = analysis.absolute_change(from_value, to_value)
            change_text = f"{change:+.2f}" if change is not None else "n/a"
        rows.append(
            html.Tr([
                html.Td(label),
                html.Td(_format_value(from_value)),
                html.Td(_format_value(to_value)),
                html.Td(change_text),
            ])
        )
    return html.Table(
        [html.Thead(html.Tr([html.Th("Metric"), html.Th(str(year_from)), html.Th(str(year_to)), html.Th("Change")]))]
        + [html.Tbody(rows)],
        style={"borderCollapse": "collapse", "width": "100%"},
    )
```

- [ ] **Step 2: Commit**

```bash
git add pages/compare_years.py
git commit -m "$(cat <<'EOF'
Add Compare Years page (/compare)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Manual verification — Compare Years

**Files:** none (verification only).

- [ ] **Step 1: Boot the app**

Run: `python app.py` (leave running)

- [ ] **Step 2: Check the page loads and updates**

Open `http://127.0.0.1:8050/compare`. Confirm the table renders with the default 1990 → latest-year comparison and all four rows show real numbers (not all "n/a"). Change "From year" to a recent year close to "To year" and confirm the change column updates to a small delta. Set both dropdowns to the same year and confirm every change shows `+0.0%` / `+0.00` rather than crashing.

- [ ] **Step 3: Stop the app**

Find and kill the `python app.py` process before moving on.

---

### Task 9: `q4_charts.py` — extract `_prepare()`, add `outlier_details()`

**Files:**
- Modify: `q4_charts.py`
- Test: `tests/test_q4_charts.py`

**Interfaces:**
- Produces: `POTENTIAL_UNITS: dict` (`{"solar": "kWh/m2/day", "wind": "m/s"}`) — used by `pages/q4_renewables.py` (Task 10) to label outlier values.
- Produces: `outlier_details(energy_df: pd.DataFrame, climatology_df: pd.DataFrame, potential: str = "solar", n: int = 3) -> dict` — returns `{"leaders": [...], "under_utilisers": [...]}`, each a list of up to `n` dicts with keys `country`, the potential column name (`solar_kwh_per_m2_day` or `wind_speed_ms`), `renewables_share_elec`, and `residual`. `leaders` = furthest **above** the fitted trend (highest residual first); `under_utilisers` = furthest **below** (lowest residual first).
- Modifies (internal refactor, same public behavior): `renewable_potential_vs_adoption_bubble()` now calls the extracted `_prepare()` helper instead of duplicating the merge/dropna/residual logic — existing `test_trend_residuals_is_zero_for_points_exactly_on_the_line` and `test_top_extremes_returns_furthest_above_and_below_the_trend` tests must keep passing unchanged.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_q4_charts.py`:

```python
from q4_charts import outlier_details


def test_outlier_details_returns_top_and_bottom_by_residual():
    energy_df = pd.DataFrame({
        "iso_code": ["AAA", "BBB", "CCC", "DDD"],
        "country": ["A", "B", "C", "D"],
        "population": [1_000_000] * 4,
        "renewables_share_elec": [1.0, 20.0, 30.0, 90.0],
    })
    climatology_df = pd.DataFrame({
        "iso_code": ["AAA", "BBB", "CCC", "DDD"],
        "solar_kwh_per_m2_day": [1.0, 2.0, 3.0, 4.0],
    })

    result = outlier_details(energy_df, climatology_df, potential="solar", n=1)

    assert result["leaders"][0]["country"] == "D"
    assert result["under_utilisers"][0]["country"] == "A"
    assert set(result["leaders"][0].keys()) == {
        "country", "solar_kwh_per_m2_day", "renewables_share_elec", "residual",
    }
    assert result["leaders"][0]["residual"] > result["under_utilisers"][0]["residual"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_q4_charts.py -v`
Expected: FAIL with `ImportError: cannot import name 'outlier_details'`.

- [ ] **Step 3: Refactor and implement in `q4_charts.py`**

Replace the body of `q4_charts.py` from the `renewable_potential_vs_adoption_bubble` function onward (i.e. everything after `top_extremes`) with:

```python
POTENTIAL_UNITS = {"solar": "kWh/m2/day", "wind": "m/s"}


def _prepare(energy_df: pd.DataFrame, climatology_df: pd.DataFrame, potential: str):
    """Shared merge + residual computation used by both the bubble chart and
    outlier_details, so the two never drift out of sync on filtering logic."""
    potential_col = POTENTIAL_COLUMNS[potential]
    merged = energy_df.merge(climatology_df, on="iso_code", how="inner")
    merged = merged.dropna(subset=[potential_col, RENEWABLE_SHARE_COLUMN, "population"])
    merged["residual"] = trend_residuals(merged[potential_col], merged[RENEWABLE_SHARE_COLUMN])
    return merged, potential_col


def renewable_potential_vs_adoption_bubble(energy_df: pd.DataFrame, climatology_df: pd.DataFrame, potential: str = "solar"):
    """Bubble scatter: x = solar/wind potential, y = renewable electricity
    share, sized by population. The 3 countries furthest above and below a
    fitted trend line are labeled — the gap between natural potential and
    actual adoption is the point of this chart.
    """
    merged, potential_col = _prepare(energy_df, climatology_df, potential)

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
        xaxis_title=f"{potential.title()} potential ({POTENTIAL_UNITS[potential]})",
        yaxis_title="Renewable share of electricity (%)",
    )
    return fig


def outlier_details(energy_df: pd.DataFrame, climatology_df: pd.DataFrame, potential: str = "solar", n: int = 3) -> dict:
    """Countries furthest above/below the fitted adoption-vs-potential trend,
    each as a dict with country, potential value, renewable share, and
    residual — the data behind the Q4 "Adoption Leaders" /
    "Potential Under-Utilisers" callouts. Not a causal claim: a country
    above the trend has relatively high adoption *for its measured
    potential*, nothing more.
    """
    merged, potential_col = _prepare(energy_df, climatology_df, potential)
    ranked = merged.sort_values("residual")
    columns = ["country", potential_col, RENEWABLE_SHARE_COLUMN, "residual"]
    under_utilisers = ranked.head(n)[columns].to_dict("records")
    leaders = ranked.tail(n)[columns].iloc[::-1].to_dict("records")
    return {"leaders": leaders, "under_utilisers": under_utilisers}
```

Note: `xaxis_title` previously used an inline conditional (`'kWh/m2/day' if potential == 'solar' else 'm/s'`) — this is now `POTENTIAL_UNITS[potential]`, same values, no behavior change.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_q4_charts.py -v`
Expected: PASS (all tests in the file, including the two pre-existing ones).

- [ ] **Step 5: Commit**

```bash
git add q4_charts.py tests/test_q4_charts.py
git commit -m "$(cat <<'EOF'
Add outlier_details() to q4_charts for the Adoption Leaders callout

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: `pages/q4_renewables.py` — render the outlier callouts

**Files:**
- Modify: `pages/q4_renewables.py`

**Interfaces:**
- Consumes: `q4_charts.outlier_details`, `q4_charts.POTENTIAL_COLUMNS`, `q4_charts.POTENTIAL_UNITS` (Task 9); `data.energy.RENEWABLE_SHARE_COLUMN`.

- [ ] **Step 1: Add the `RENEWABLE_SHARE_COLUMN` import**

In `pages/q4_renewables.py`, change:

```python
from data.energy import ENERGY_MAX_YEAR
```

to:

```python
from data.energy import ENERGY_MAX_YEAR, RENEWABLE_SHARE_COLUMN
```

- [ ] **Step 2: Add the outlier container to the layout**

In `pages/q4_renewables.py`, change:

```python
        dcc.Graph(id="q4-bubble"),
    ])
```

to:

```python
        dcc.Graph(id="q4-bubble"),
        html.Div(
            id="q4-outliers",
            style={"display": "flex", "gap": "40px", "flexWrap": "wrap", "marginTop": "20px"},
        ),
    ])
```

- [ ] **Step 3: Extend the `update_q4` callback to also output the outlier lists**

In `pages/q4_renewables.py`, replace:

```python
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
```

with:

```python
def _outlier_item(row, potential_col, unit):
    return html.Li(
        f"{row['country']} — {row[RENEWABLE_SHARE_COLUMN]:.0f}% renewable electricity "
        f"(potential {row[potential_col]:.1f} {unit})"
    )


@dash.callback(
    Output("q4-bubble", "figure"),
    Output("q4-outliers", "children"),
    Input("q4-year-slider", "value"),
    Input("q4-potential-toggle", "value"),
)
def update_q4(year, potential):
    energy_year = _energy_for_year(year)
    fig = q4_charts.renewable_potential_vs_adoption_bubble(
        energy_year, state.loaded.climatology, potential=potential
    )

    outliers = q4_charts.outlier_details(energy_year, state.loaded.climatology, potential=potential)
    potential_col = q4_charts.POTENTIAL_COLUMNS[potential]
    unit = q4_charts.POTENTIAL_UNITS[potential]

    outlier_children = [
        html.Div(
            style={"flex": "1", "minWidth": "280px"},
            children=[
                html.H4("\U0001F680 Adoption Leaders"),
                html.P(
                    "Above the fitted trend: renewable adoption is relatively high "
                    "compared with measured solar/wind potential."
                ),
                html.Ul([_outlier_item(row, potential_col, unit) for row in outliers["leaders"]]),
            ],
        ),
        html.Div(
            style={"flex": "1", "minWidth": "280px"},
            children=[
                html.H4("⚠️ Potential Under-Utilisers"),
                html.P(
                    "Below the fitted trend: renewable adoption is relatively low "
                    "compared with measured solar/wind potential."
                ),
                html.Ul([_outlier_item(row, potential_col, unit) for row in outliers["under_utilisers"]]),
            ],
        ),
    ]
    return fig, outlier_children
```

- [ ] **Step 4: Run the existing test suite to confirm nothing else broke**

Run: `pytest tests/ -q`
Expected: PASS, `18 + <new tests from Tasks 1-4, 9> passed`.

- [ ] **Step 5: Commit**

```bash
git add pages/q4_renewables.py
git commit -m "$(cat <<'EOF'
Render Adoption Leaders / Potential Under-Utilisers callouts on Q4

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: Manual verification — Q4 outlier callouts

**Files:** none (verification only).

- [ ] **Step 1: Boot the app**

Run: `python app.py` (leave running)

- [ ] **Step 2: Check the callouts render and respond to controls**

Open `http://127.0.0.1:8050/q4`. Confirm two columns appear below the bubble chart: "🚀 Adoption Leaders" and "⚠️ Potential Under-Utilisers", each listing 3 countries with a renewable-% and potential value. Move the year slider and confirm the lists update. Toggle Solar/Wind and confirm the potential values and unit label change accordingly (`kWh/m2/day` vs `m/s`).

- [ ] **Step 3: Stop the app**

Find and kill the `python app.py` process before moving on.

---

### Task 12: Update documentation and run the full suite

**Files:**
- Modify: `docs/PROJECT_REPORT.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Run the full test suite one more time**

Run: `pytest tests/ -q`
Expected: PASS, all tests (18 original + new ones from Tasks 1, 2, 3, 4, 9).

- [ ] **Step 2: Update `docs/PROJECT_REPORT.md` §11**

In `docs/PROJECT_REPORT.md`, change the heading and intro of the "Committed for the next phase (Priority 1)" list from:

```
### Committed for the next phase (Priority 1)
```

to:

```
### Shipped (Priority 1)
```

- [ ] **Step 3: Update `CLAUDE.md`'s file table**

In `CLAUDE.md`, change the row:

```
| `analysis.py` | Pure Q1 trend helpers (rolling growth average, period means) — unit-tested apart from plotting | Done |
```

to:

```
| `analysis.py` | Pure numeric helpers: Q1 trend helpers, plus generic country-series/year-comparison helpers used by the Country Profile and Compare Years pages | Done |
```

and change:

```
| `q4_charts.py` | Q4 chart: renewable-adoption-vs-potential bubble, with trend-residual labelling | Done |
```

to:

```
| `q4_charts.py` | Q4 chart: renewable-adoption-vs-potential bubble with trend-residual labelling, plus `outlier_details()` for the Adoption Leaders / Potential Under-Utilisers callouts | Done |
```

and add, after the `pages/q4_renewables.py` row:

```
| `country_profile_charts.py` | Country Climate Profile: trend-sparkline chart builder | Done |
| `pages/country_profile.py` | Country Profile page (`/country`): country picker, KPI cards, 1990-present trend sparklines | Done |
| `pages/compare_years.py` | Compare Years page (`/compare`): pick two years, see global CO2 / CO2-per-person / renewables / temperature deltas | Done |
```

- [ ] **Step 4: Update `CLAUDE.md`'s "Next task" section**

Change:

```
- Push this repo to GitHub, then create a Render Web Service from it.
```

to:

```
- Repo is pushed to GitHub (`chandan12ar/global-climate-trends-dashboard`, private). Create a Render Web Service from it.
```

and change:

```
- After deploy, sanity-check the live URL: all five pages (`/`, `/q1`, `/q2`,
  `/q3`, `/q4`) load, every slider/dropdown/toggle updates its charts, and
  the CSV download buttons on Q2/Q3/Q4 work.
```

to:

```
- After deploy, sanity-check the live URL: all seven pages (`/`, `/q1`,
  `/q2`, `/q3`, `/q4`, `/country`, `/compare`) load, every slider/dropdown/
  toggle updates its charts, and the CSV download buttons on Q2/Q3/Q4 work.
```

- [ ] **Step 5: Commit**

```bash
git add docs/PROJECT_REPORT.md CLAUDE.md
git commit -m "$(cat <<'EOF'
Mark Priority 1 enhancements shipped in project docs

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```
