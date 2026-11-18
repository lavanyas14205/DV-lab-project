# AI Footprint Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new "AI Footprint" utility page to the Global Climate Trends dashboard that estimates the water/energy/carbon cost of using an AI model per prompt, compares models side-by-side, scales to a usage habit, and contextualizes the result against a real country's per-capita CO2 (already in the app's data).

**Architecture:** A new curated static CSV (`data/ai_footprint.csv`) loaded the same way as every other `data/*.py` source, two new pure/testable helper functions (`ai_footprint_analysis.py`), two new chart-building functions (`ai_footprint_charts.py`), and one new Dash page (`pages/ai_footprint.py`) wired into the existing `LoadedData`/`load_all()`/`state.py` machinery. No new runtime dependencies, no network calls.

**Tech Stack:** Python, pandas, Plotly (`plotly.graph_objects`, `plotly.subplots.make_subplots`), Dash (`dash.register_page`, `dcc`, `html`), pytest.

**Spec:** `docs/superpowers/specs/2026-09-16-ai-footprint-page-design.md`

## Global Constraints

- Free tier only — no paid services, no API keys, no new runtime dependencies (everything needed is already in `requirements.txt`).
- No live network calls from the running app for this feature — `data/ai_footprint.csv` is a static, committed reference table, read the same way `data/climatology.py` reads `power_climatology.csv`.
- Every number in `data/ai_footprint.csv` is a modeled estimate derived from published studies, not a measurement — this must be visibly disclosed on the page (a permanent banner, not dismissible), matching the existing "modelled vs. measured" temperature rule already in `CLAUDE.md`.
- Follow this repo's existing split: pure, non-plotting logic (loaders, `analysis.py`-style helpers) is TDD'd with pytest; chart-building functions (`prototype_charts.py`, `q4_charts.py` style) and Dash page layouts/callbacks are verified by running `python app.py` in a browser, not unit-tested — this project has never deviated from that split, and this plan doesn't either.
- Match existing naming/style conventions exactly: `snake_case` module-level constants in caps (`AI_FOOTPRINT_PATH`, `ENERGY_MAX_YEAR`-style), `_leading_underscore` for page-private module constants, `_kpi_card`-style small private helpers duplicated per-page rather than shared (this project already does this in `pages/country_profile.py`; don't introduce a shared UI-helpers module for one function).

---

### Task 1: `data/ai_footprint.py` loader

**Files:**
- Create: `data/ai_footprint.py`
- Test: `tests/test_ai_footprint.py`

**Interfaces:**
- Produces: `AI_FOOTPRINT_PATH: str`, `load_ai_footprint_data(path: str = AI_FOOTPRINT_PATH) -> pd.DataFrame`

- [ ] **Step 1: Write the failing test**

Create `tests/test_ai_footprint.py`:

```python
from pathlib import Path

import pandas as pd

from data.ai_footprint import load_ai_footprint_data

AI_FOOTPRINT_CSV = Path(__file__).resolve().parent.parent / "data" / "ai_footprint.csv"


def test_load_ai_footprint_data_reads_expected_columns(tmp_path):
    csv_text = (
        "model,use_case,energy_wh,co2_g,water_ml,word_count_max,source\n"
        "ChatGPT,simple_qa,0.16,0.04,0.32,15,test\n"
    )
    path = tmp_path / "ai_footprint.csv"
    path.write_text(csv_text)

    result = load_ai_footprint_data(str(path))

    assert list(result.columns) == [
        "model", "use_case", "energy_wh", "co2_g", "water_ml", "word_count_max", "source",
    ]
    assert result.iloc[0]["model"] == "ChatGPT"
    assert result.iloc[0]["energy_wh"] == 0.16
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ai_footprint.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data.ai_footprint'`

- [ ] **Step 3: Write minimal implementation**

Create `data/ai_footprint.py`:

```python
"""Curated AI-model footprint reference table.

data/ai_footprint.csv holds hand-derived, per-model per-use-case estimates
of energy (Wh), carbon (gCO2e), and water (mL) cost per AI query. These are
NOT measured or vendor-disclosed figures -- there is no standardized,
comprehensive measurement of per-query AI cost (MIT News, "Explained:
Generative AI's environmental impact", Jan 2025,
https://news.mit.edu/2025/explained-generative-ai-environmental-impact-0117).
Every row's magnitude is anchored to two numbers from that article: a
ChatGPT query uses ~5x the electricity of a basic web search, and data
centers need ~2L of water per kWh consumed for cooling (so water_ml =
energy_wh * 2 throughout the table). The ChatGPT / email_summary row is
additionally cross-checked for plausible order of magnitude -- not copied
-- against the ClimateAligned AI Footprint Calculator's displayed GPT-4o
"median use" figures
(https://www.climatealigned.co/tools/ai-footprint-calculator), which cites
Google's 2024 production measurements.

Model-to-model multipliers relative to the ChatGPT baseline (Claude 0.9x,
Gemini 0.75x, Grok 1.15x) are this project's own rough, qualitative
estimate based on public reporting about relative model/infrastructure
scale -- an explicitly unverified assumption, not a measurement. The same
caveat is shown to users in the AI Footprint page's on-page disclosure
banner (pages/ai_footprint.py).

word_count_max buckets the free-text prompt input by word count (see
ai_footprint_analysis.bucket_prompt); 100000 represents "no cap" for the
largest (coding_agent) use case.
"""

from pathlib import Path

import pandas as pd

AI_FOOTPRINT_PATH = str(Path(__file__).resolve().parent / "ai_footprint.csv")


def load_ai_footprint_data(path: str = AI_FOOTPRINT_PATH) -> pd.DataFrame:
    return pd.read_csv(path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ai_footprint.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add data/ai_footprint.py tests/test_ai_footprint.py
git commit -m "feat: add AI footprint data loader"
```

---

### Task 2: `data/ai_footprint.csv` curated reference table + data-integrity tests

**Files:**
- Create: `data/ai_footprint.csv`
- Modify: `tests/test_ai_footprint.py`

**Interfaces:**
- Consumes: nothing new (reads the file via `pd.read_csv` directly in the test, same as `tests/test_capitals.py` does for `data/capitals.csv`)
- Produces: the real `data/ai_footprint.csv` on disk — 4 models (`ChatGPT`, `Claude`, `Gemini`, `Grok`) x 4 use cases (`simple_qa`, `email_summary`, `document_review`, `coding_agent`) = 16 rows. Every later task (analysis, charts, page) depends on these exact model and use_case string values.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_ai_footprint.py`:

```python
def _load_real_csv():
    return pd.read_csv(AI_FOOTPRINT_CSV)


def test_ai_footprint_csv_has_expected_columns():
    df = _load_real_csv()
    assert list(df.columns) == [
        "model", "use_case", "energy_wh", "co2_g", "water_ml", "word_count_max", "source",
    ]


def test_ai_footprint_csv_has_all_sixteen_model_use_case_combinations():
    df = _load_real_csv()
    expected_models = {"ChatGPT", "Claude", "Gemini", "Grok"}
    expected_use_cases = {"simple_qa", "email_summary", "document_review", "coding_agent"}
    assert set(df["model"]) == expected_models
    assert set(df["use_case"]) == expected_use_cases
    assert len(df) == 16
    assert not df.duplicated(subset=["model", "use_case"]).any()


def test_ai_footprint_csv_has_no_missing_footprint_values():
    df = _load_real_csv()
    assert df[["energy_wh", "co2_g", "water_ml"]].notna().all().all()


def test_ai_footprint_csv_word_count_max_is_consistent_within_each_use_case():
    """Every model's row for a given use_case must share the same
    word_count_max -- ai_footprint_analysis.bucket_prompt() (Task 4)
    de-duplicates on (use_case, word_count_max) and would silently pick an
    arbitrary one if they disagreed."""
    df = _load_real_csv()
    per_use_case = df.groupby("use_case")["word_count_max"].nunique()
    assert (per_use_case == 1).all()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ai_footprint.py -v`
Expected: FAIL — `FileNotFoundError` (or empty-data error) since `data/ai_footprint.csv` doesn't exist yet

- [ ] **Step 3: Create the real CSV**

Create `data/ai_footprint.csv` with exactly this content:

```csv
model,use_case,energy_wh,co2_g,water_ml,word_count_max,source
ChatGPT,simple_qa,0.16,0.04,0.32,15,"MIT News 2025: ~5x a web search; scaled down for a short-prompt use case"
ChatGPT,email_summary,0.486,0.13,0.97,60,"MIT News 2025 / Google 2024 production measurements (GPT-4o baseline, median use)"
ChatGPT,document_review,2.50,0.67,5.00,200,"Scaled from the ChatGPT median-use baseline for a longer, multi-paragraph task"
ChatGPT,coding_agent,15.00,4.01,30.00,100000,"Scaled from the ChatGPT median-use baseline for a multi-step coding/agent turn"
Claude,simple_qa,0.14,0.04,0.28,15,"Scaled from the ChatGPT baseline by an estimated 0.9x relative-efficiency factor (unverified assumption, see data/ai_footprint.py)"
Claude,email_summary,0.44,0.12,0.87,60,"Scaled from the ChatGPT baseline by an estimated 0.9x relative-efficiency factor (unverified assumption, see data/ai_footprint.py)"
Claude,document_review,2.25,0.60,4.50,200,"Scaled from the ChatGPT baseline by an estimated 0.9x relative-efficiency factor (unverified assumption, see data/ai_footprint.py)"
Claude,coding_agent,13.50,3.60,27.00,100000,"Scaled from the ChatGPT baseline by an estimated 0.9x relative-efficiency factor (unverified assumption, see data/ai_footprint.py)"
Gemini,simple_qa,0.12,0.03,0.24,15,"Scaled from the ChatGPT baseline by an estimated 0.75x relative-efficiency factor (unverified assumption, see data/ai_footprint.py)"
Gemini,email_summary,0.36,0.10,0.73,60,"Scaled from the ChatGPT baseline by an estimated 0.75x relative-efficiency factor (unverified assumption, see data/ai_footprint.py)"
Gemini,document_review,1.88,0.50,3.75,200,"Scaled from the ChatGPT baseline by an estimated 0.75x relative-efficiency factor (unverified assumption, see data/ai_footprint.py)"
Gemini,coding_agent,11.25,3.00,22.50,100000,"Scaled from the ChatGPT baseline by an estimated 0.75x relative-efficiency factor (unverified assumption, see data/ai_footprint.py)"
Grok,simple_qa,0.18,0.05,0.37,15,"Scaled from the ChatGPT baseline by an estimated 1.15x relative-efficiency factor (unverified assumption, see data/ai_footprint.py)"
Grok,email_summary,0.56,0.15,1.12,60,"Scaled from the ChatGPT baseline by an estimated 1.15x relative-efficiency factor (unverified assumption, see data/ai_footprint.py)"
Grok,document_review,2.88,0.77,5.75,200,"Scaled from the ChatGPT baseline by an estimated 1.15x relative-efficiency factor (unverified assumption, see data/ai_footprint.py)"
Grok,coding_agent,17.25,4.61,34.50,100000,"Scaled from the ChatGPT baseline by an estimated 1.15x relative-efficiency factor (unverified assumption, see data/ai_footprint.py)"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ai_footprint.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add data/ai_footprint.csv tests/test_ai_footprint.py
git commit -m "feat: add curated AI footprint reference table"
```

---

### Task 3: Wire `ai_footprint` into `data/__init__.py`

**Files:**
- Modify: `data/__init__.py`

**Interfaces:**
- Consumes: `data.ai_footprint.AI_FOOTPRINT_PATH`, `data.ai_footprint.load_ai_footprint_data` (Task 1)
- Produces: `LoadedData.ai_footprint: pd.DataFrame`, available at `state.loaded.ai_footprint` after this task — every later task reads the reference table through this attribute, never by calling `load_ai_footprint_data` directly.

- [ ] **Step 1: Modify `data/__init__.py`**

Add the import (after the existing `from .co2 import (...)` block, alongside the other single-line source imports):

```python
from .ai_footprint import AI_FOOTPRINT_PATH, load_ai_footprint_data
```

Add `"AI_FOOTPRINT_PATH", "load_ai_footprint_data",` to the `__all__` list (anywhere among the other loader/constant names).

Add the field to `LoadedData`:

```python
@dataclass
class LoadedData:
    co2_all: pd.DataFrame
    co2_countries: pd.DataFrame
    temperature: pd.DataFrame
    energy: pd.DataFrame
    climatology: pd.DataFrame
    ai_footprint: pd.DataFrame
```

Add the parameter and loading call to `load_all()`:

```python
def load_all(
    co2_path: str = CO2_URL,
    gistemp_path: str = GISTEMP_URL,
    energy_path: str = ENERGY_URL,
    climatology_path: str = CLIMATOLOGY_PATH,
    ai_footprint_path: str = AI_FOOTPRINT_PATH,
) -> LoadedData:
    """Load once at startup. Returns every frame the app needs."""
    co2_all = load_co2_data(co2_path)
    co2_countries = filter_countries(co2_all)
    temperature = load_temperature_data(gistemp_path)
    energy = load_energy_data(energy_path)
    climatology = load_climatology_data(climatology_path)
    ai_footprint = load_ai_footprint_data(ai_footprint_path)
    return LoadedData(
        co2_all=co2_all,
        co2_countries=co2_countries,
        temperature=temperature,
        energy=energy,
        climatology=climatology,
        ai_footprint=ai_footprint,
    )
```

- [ ] **Step 2: Verify the dataclass field was wired correctly (no network needed)**

Run: `python -c "from data import LoadedData; print('ai_footprint' in LoadedData.__dataclass_fields__)"`
Expected: prints `True`

- [ ] **Step 3: Run the full existing test suite to confirm nothing else broke**

Run: `pytest tests/ -v -k "not covers_every_country"`

(The `-k` filter skips `test_capitals.py`'s one network-dependent test, which needs the live OWID CO2 file — not relevant to this change and not something this task should depend on network access to verify.)

Expected: PASS, no new failures

- [ ] **Step 4: Commit**

```bash
git add data/__init__.py
git commit -m "feat: wire ai_footprint into LoadedData and load_all"
```

---

### Task 4: `ai_footprint_analysis.bucket_prompt`

**Files:**
- Create: `ai_footprint_analysis.py`
- Create: `tests/test_ai_footprint_analysis.py`

**Interfaces:**
- Produces: `bucket_prompt(text: str, footprint: pd.DataFrame) -> str | None`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ai_footprint_analysis.py`:

```python
import pandas as pd

from ai_footprint_analysis import bucket_prompt


def _footprint_fixture():
    """A minimal footprint frame with the (use_case, word_count_max) shape
    bucket_prompt reads -- duplicated across two models, same as the real
    16-row table, to prove drop_duplicates handles that correctly."""
    return pd.DataFrame({
        "model": ["ChatGPT", "Claude"] * 4,
        "use_case": [
            "simple_qa", "simple_qa",
            "email_summary", "email_summary",
            "document_review", "document_review",
            "coding_agent", "coding_agent",
        ],
        "word_count_max": [15, 15, 60, 60, 200, 200, 100000, 100000],
    })


def _words(n):
    return " ".join(["word"] * n)


def test_bucket_prompt_at_lower_boundary_word_count():
    result = bucket_prompt(_words(15), _footprint_fixture())
    assert result == "simple_qa"


def test_bucket_prompt_one_word_over_boundary_moves_to_next_bucket():
    result = bucket_prompt(_words(16), _footprint_fixture())
    assert result == "email_summary"


def test_bucket_prompt_at_email_summary_upper_boundary():
    result = bucket_prompt(_words(60), _footprint_fixture())
    assert result == "email_summary"


def test_bucket_prompt_at_document_review_boundary():
    result = bucket_prompt(_words(200), _footprint_fixture())
    assert result == "document_review"


def test_bucket_prompt_far_over_document_review_falls_into_coding_agent():
    result = bucket_prompt(_words(201), _footprint_fixture())
    assert result == "coding_agent"


def test_bucket_prompt_empty_string_returns_none():
    assert bucket_prompt("", _footprint_fixture()) is None


def test_bucket_prompt_whitespace_only_returns_none():
    assert bucket_prompt("   ", _footprint_fixture()) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ai_footprint_analysis.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ai_footprint_analysis'`

- [ ] **Step 3: Write minimal implementation**

Create `ai_footprint_analysis.py`:

```python
"""Pure analytical helpers for the AI Footprint page. Kept separate and
pure so they're unit-testable without touching Dash/plotting code -- same
reasoning as analysis.py for the research-question pages.
"""

import pandas as pd


def bucket_prompt(text: str, footprint: pd.DataFrame) -> str | None:
    """Map free-text prompt length to a use_case from `footprint`'s
    word_count_max column. None for empty/whitespace-only text -- the
    caller falls back to the dropdown's selected use case in that case.
    """
    word_count = len(text.split())
    if word_count == 0:
        return None

    thresholds = (
        footprint[["use_case", "word_count_max"]]
        .drop_duplicates()
        .sort_values("word_count_max")
    )
    for _, row in thresholds.iterrows():
        if word_count <= row["word_count_max"]:
            return row["use_case"]
    return thresholds.iloc[-1]["use_case"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ai_footprint_analysis.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add ai_footprint_analysis.py tests/test_ai_footprint_analysis.py
git commit -m "feat: add bucket_prompt for AI footprint use-case detection"
```

---

### Task 5: `ai_footprint_analysis.per_capita_share`

**Files:**
- Modify: `ai_footprint_analysis.py`
- Modify: `tests/test_ai_footprint_analysis.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `per_capita_share(total_co2_g: float, country_annual_co2_per_capita_t: float | None) -> float | None`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_ai_footprint_analysis.py`:

```python
from ai_footprint_analysis import per_capita_share


def test_per_capita_share_computes_percentage_of_annual_country_co2():
    # 1,000,000 g = 1 tonne; 1 / 5.0 tonnes = 20%
    result = per_capita_share(1_000_000, 5.0)
    assert result == 20.0


def test_per_capita_share_returns_none_when_country_value_is_missing():
    assert per_capita_share(1_000_000, None) is None


def test_per_capita_share_returns_none_when_country_value_is_zero():
    assert per_capita_share(1_000_000, 0.0) is None


def test_per_capita_share_returns_zero_for_zero_usage():
    assert per_capita_share(0, 5.0) == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ai_footprint_analysis.py -v`
Expected: FAIL with `ImportError: cannot import name 'per_capita_share'`

- [ ] **Step 3: Write minimal implementation**

Add to `ai_footprint_analysis.py`:

```python
def per_capita_share(
    total_co2_g: float, country_annual_co2_per_capita_t: float | None
) -> float | None:
    """What percentage of one person's annual CO2 footprint in a country
    `total_co2_g` (grams) represents. None if the country has no per-capita
    CO2 value for its latest year -- never a fabricated 0%, same
    None-on-missing-data convention as analysis.value_at_year.
    """
    if country_annual_co2_per_capita_t is None or country_annual_co2_per_capita_t == 0:
        return None
    total_co2_t = total_co2_g / 1_000_000
    return total_co2_t / country_annual_co2_per_capita_t * 100
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ai_footprint_analysis.py -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Commit**

```bash
git add ai_footprint_analysis.py tests/test_ai_footprint_analysis.py
git commit -m "feat: add per_capita_share for AI footprint country comparison"
```

---

### Task 6: `ai_footprint_charts.py`

**Files:**
- Create: `ai_footprint_charts.py`

**Interfaces:**
- Consumes: a `footprint` DataFrame shaped like `data/ai_footprint.csv` (columns `model, use_case, energy_wh, co2_g, water_ml`)
- Produces: `model_comparison_bar(footprint: pd.DataFrame, use_case: str, models: list[str]) -> plotly.graph_objects.Figure`, `per_capita_comparison(share_pct: float | None, country: str) -> plotly.graph_objects.Figure`

This task has no pytest step — consistent with `prototype_charts.py` and the plotting half of `q4_charts.py`, figure-building functions in this project are verified by running the app and looking at the chart (Task 8), not unit-tested. Step 2 below is a quick manual sanity check that the function runs without raising, not a permanent test.

- [ ] **Step 1: Write the implementation**

Create `ai_footprint_charts.py`:

```python
"""AI Footprint page charts: per-model comparison and per-capita context."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

_METRICS = [
    ("energy_wh", "Energy (Wh)"),
    ("co2_g", "Carbon (gCO2e)"),
    ("water_ml", "Water (mL)"),
]


def model_comparison_bar(footprint, use_case, models):
    """One subplot per metric (each has its own unit, so they don't share
    a y-axis), one bar per model, for the selected use case."""
    subset = footprint[(footprint["use_case"] == use_case) & (footprint["model"].isin(models))]
    fig = make_subplots(rows=1, cols=3, subplot_titles=[label for _, label in _METRICS])
    for i, (column, _label) in enumerate(_METRICS, start=1):
        fig.add_trace(go.Bar(x=subset["model"], y=subset[column], showlegend=False), row=1, col=i)
    fig.update_layout(title=f"Per-query footprint by model — {use_case}")
    return fig


def per_capita_comparison(share_pct, country):
    """Single bar: projected AI usage as % of one person's annual
    per-capita CO2 in `country`. share_pct is None when the country has no
    per-capita CO2 data for its latest year -- shown as an annotation, not
    a fake 0%.
    """
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[country], y=[share_pct if share_pct is not None else 0], name="AI usage"))
    fig.update_layout(
        title=f"Projected AI usage as % of {country}'s per-capita annual CO2",
        yaxis_title="% of one person's annual CO2 footprint",
    )
    if share_pct is None:
        fig.add_annotation(
            text="No per-capita CO2 data for this country's latest year",
            showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper",
        )
    return fig
```

- [ ] **Step 2: Manually verify both functions run without error**

Run:

```bash
python -c "
import pandas as pd
import ai_footprint_charts as c

footprint = pd.read_csv('data/ai_footprint.csv')
fig1 = c.model_comparison_bar(footprint, 'simple_qa', ['ChatGPT', 'Claude', 'Gemini', 'Grok'])
assert len(fig1.data) == 3, f'expected 3 bar traces (one per metric), got {len(fig1.data)}'

fig2 = c.per_capita_comparison(12.5, 'India')
assert len(fig2.data) == 1
fig3 = c.per_capita_comparison(None, 'India')
assert len(fig3.layout.annotations) == 1
print('OK')
"
```

Expected: prints `OK`

- [ ] **Step 3: Commit**

```bash
git add ai_footprint_charts.py
git commit -m "feat: add AI footprint model-comparison and per-capita charts"
```

---

### Task 7: `pages/ai_footprint.py`

**Files:**
- Create: `pages/ai_footprint.py`

**Interfaces:**
- Consumes: `state.loaded.ai_footprint`, `state.loaded.co2_countries` (Task 3); `ai_footprint_analysis.bucket_prompt`, `ai_footprint_analysis.per_capita_share` (Tasks 4-5); `ai_footprint_charts.model_comparison_bar`, `ai_footprint_charts.per_capita_comparison` (Task 6); `analysis.country_series`, `analysis.latest_value`, `analysis.top_emitter` (already in the repo)
- Produces: the registered `/ai-footprint` page — nothing else depends on this page's internals

This task has no pytest step — Dash pages in this project are verified by running the app in a browser (`python app.py`), same as every other `pages/*.py` module.

- [ ] **Step 1: Write the page**

Create `pages/ai_footprint.py`:

```python
"""AI Footprint page: estimated water/energy/carbon cost of an AI prompt,
contextualized against real per-country CO2 data already in the app.

Reference numbers in data/ai_footprint.csv are modeled estimates from
published studies (see data/ai_footprint.py's docstring), not real-time
measurements -- the disclosure banner below says so to the user too.
"""

import io

import dash
from dash import Input, Output, dcc, html

import ai_footprint_analysis
import ai_footprint_charts
import analysis
import state

dash.register_page(__name__, path="/ai-footprint", name="AI Footprint", order=7)

_MODEL_OPTIONS = sorted(state.loaded.ai_footprint["model"].unique())
_DEFAULT_MODEL = _MODEL_OPTIONS[0]

_USE_CASE_LABELS = {
    "simple_qa": "Simple Q&A",
    "email_summary": "Email / Summary",
    "document_review": "Document Review",
    "coding_agent": "Coding / Agent Session",
}
_USE_CASE_ORDER = (
    state.loaded.ai_footprint[["use_case", "word_count_max"]]
    .drop_duplicates()
    .sort_values("word_count_max")["use_case"]
    .tolist()
)
_USE_CASE_OPTIONS = [{"label": _USE_CASE_LABELS[uc], "value": uc} for uc in _USE_CASE_ORDER]
_DEFAULT_USE_CASE = _USE_CASE_ORDER[0]

_COUNTRY_OPTIONS = sorted(state.loaded.co2_countries["country"].unique())
_LATEST_YEAR = int(state.loaded.co2_countries["year"].max())
_DEFAULT_COUNTRY = analysis.top_emitter(state.loaded.co2_countries, _LATEST_YEAR)

_WEEKS_PER_MONTH = 52 / 12


def layout():
    return html.Div([
        html.H2("AI Footprint"),
        html.P(
            "These are modeled estimates derived from published third-party studies "
            "(MIT News, Jan 2025; Google's 2024 production measurements), not "
            "real-time measurements. Actual per-query cost varies by hardware, "
            "region, and model version. The water comparison uses a global "
            "average, not a country-specific figure.",
            style={
                "fontSize": "0.85em", "color": "#555", "background": "#f5f5f5",
                "padding": "10px", "borderRadius": "4px",
            },
        ),
        html.Div(
            style={
                "display": "flex", "gap": "30px", "flexWrap": "wrap",
                "alignItems": "flex-end", "marginTop": "15px",
            },
            children=[
                html.Div(
                    style={"minWidth": "220px"},
                    children=[
                        html.Label("Models to compare:", htmlFor="ai-footprint-models"),
                        dcc.Checklist(
                            id="ai-footprint-models",
                            options=[{"label": m, "value": m} for m in _MODEL_OPTIONS],
                            value=_MODEL_OPTIONS,
                            inline=True,
                        ),
                    ],
                ),
                html.Div(
                    style={"minWidth": "220px"},
                    children=[
                        html.Label("Model for projection:", htmlFor="ai-footprint-primary-model"),
                        dcc.Dropdown(
                            id="ai-footprint-primary-model",
                            options=[{"label": m, "value": m} for m in _MODEL_OPTIONS],
                            value=_DEFAULT_MODEL,
                            clearable=False,
                        ),
                    ],
                ),
                html.Div(
                    style={"minWidth": "220px"},
                    children=[
                        html.Label("Use case:", htmlFor="ai-footprint-usecase"),
                        dcc.Dropdown(
                            id="ai-footprint-usecase",
                            options=_USE_CASE_OPTIONS,
                            value=_DEFAULT_USE_CASE,
                            clearable=False,
                        ),
                    ],
                ),
                html.Div(
                    style={"minWidth": "180px"},
                    children=[
                        html.Label("Queries per day:", htmlFor="ai-footprint-queries-per-day"),
                        dcc.Input(
                            id="ai-footprint-queries-per-day", type="number", value=10, min=0, step=1,
                        ),
                    ],
                ),
                html.Div(
                    style={"minWidth": "180px"},
                    children=[
                        html.Label("Days per week:", htmlFor="ai-footprint-days-per-week"),
                        dcc.RadioItems(
                            id="ai-footprint-days-per-week",
                            options=[{"label": "5", "value": 5}, {"label": "7", "value": 7}],
                            value=7, inline=True,
                        ),
                    ],
                ),
                html.Div(
                    style={"minWidth": "220px"},
                    children=[
                        html.Label("Compare against:", htmlFor="ai-footprint-country"),
                        dcc.Dropdown(
                            id="ai-footprint-country",
                            options=[{"label": c, "value": c} for c in _COUNTRY_OPTIONS],
                            value=_DEFAULT_COUNTRY,
                            clearable=False,
                        ),
                    ],
                ),
            ],
        ),
        html.Div(
            style={"marginTop": "15px"},
            children=[
                html.Label(
                    "Or paste an actual prompt (overrides the use case above):",
                    htmlFor="ai-footprint-prompt",
                ),
                dcc.Textarea(
                    id="ai-footprint-prompt", value="", style={"width": "100%", "height": "60px"},
                ),
            ],
        ),
        dcc.Graph(id="ai-footprint-model-bar"),
        html.Div(
            id="ai-footprint-projection-kpis",
            style={"display": "flex", "gap": "30px", "flexWrap": "wrap", "margin": "20px 0"},
        ),
        dcc.Graph(id="ai-footprint-per-capita"),
        html.Div([
            html.Button("Download reference table CSV", id="ai-footprint-download-button"),
            dcc.Download(id="ai-footprint-download-csv"),
        ]),
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
    Output("ai-footprint-model-bar", "figure"),
    Output("ai-footprint-projection-kpis", "children"),
    Output("ai-footprint-per-capita", "figure"),
    Input("ai-footprint-models", "value"),
    Input("ai-footprint-primary-model", "value"),
    Input("ai-footprint-usecase", "value"),
    Input("ai-footprint-prompt", "value"),
    Input("ai-footprint-queries-per-day", "value"),
    Input("ai-footprint-days-per-week", "value"),
    Input("ai-footprint-country", "value"),
)
def update_ai_footprint(
    models, primary_model, use_case_dropdown, prompt_text, queries_per_day, days_per_week, country
):
    footprint = state.loaded.ai_footprint
    selected_models = models or _MODEL_OPTIONS

    bucketed_use_case = ai_footprint_analysis.bucket_prompt(prompt_text or "", footprint)
    use_case = bucketed_use_case or use_case_dropdown

    bar_fig = ai_footprint_charts.model_comparison_bar(footprint, use_case, selected_models)

    per_query = footprint[
        (footprint["model"] == primary_model) & (footprint["use_case"] == use_case)
    ].iloc[0]

    monthly_queries = (queries_per_day or 0) * (days_per_week or 7) * _WEEKS_PER_MONTH
    monthly_energy_wh = per_query["energy_wh"] * monthly_queries
    monthly_co2_g = per_query["co2_g"] * monthly_queries
    monthly_water_ml = per_query["water_ml"] * monthly_queries

    kpis = [
        _kpi_card("Monthly energy", f"{monthly_energy_wh:,.1f} Wh"),
        _kpi_card("Monthly carbon", f"{monthly_co2_g:,.1f} g CO2e"),
        _kpi_card("Monthly water", f"{monthly_water_ml:,.0f} mL"),
    ]

    co2_pc_series = analysis.country_series(state.loaded.co2_countries, country, "co2_per_capita")
    latest = analysis.latest_value(co2_pc_series)
    country_co2_pc = latest[1] if latest else None
    share_pct = ai_footprint_analysis.per_capita_share(monthly_co2_g, country_co2_pc)

    per_capita_fig = ai_footprint_charts.per_capita_comparison(share_pct, country)

    return bar_fig, kpis, per_capita_fig


@dash.callback(
    Output("ai-footprint-download-csv", "data"),
    Input("ai-footprint-download-button", "n_clicks"),
    prevent_initial_call=True,
)
def download_ai_footprint(n_clicks):
    buffer = io.StringIO()
    state.loaded.ai_footprint.to_csv(buffer, index=False)
    return dict(content=buffer.getvalue(), filename="ai_footprint_reference.csv")
```

- [ ] **Step 2: Run the full pytest suite to confirm the new page doesn't break anything at import time**

Run: `pytest tests/ -v -k "not covers_every_country"`
Expected: PASS, no new failures (Dash pages are imported when `app.py` runs, not by pytest, but this catches any accidental syntax/import error in files pytest does collect)

- [ ] **Step 3: Manually verify the page in a browser**

Run: `python app.py` (starts the dev server, default `http://127.0.0.1:8050`)

In a browser, navigate to `http://127.0.0.1:8050/ai-footprint` and check:
- The page loads with the disclosure banner visible
- Unchecking/rechecking models updates the model-comparison chart (3 subplots: Energy, Carbon, Water)
- Changing "Use case" changes the bars
- Pasting a long paragraph (60+ words) into the prompt textarea switches the effective use case away from the dropdown's selection (the chart changes even though the dropdown value doesn't)
- Clearing the textarea reverts to the dropdown's use case
- Changing "Queries per day" and "Days per week" updates the three monthly KPI cards
- Changing "Compare against" updates the per-capita bar chart and its title
- "Download reference table CSV" downloads a 16-row CSV matching `data/ai_footprint.csv`
- The new "AI Footprint" link appears in the top nav (auto-generated from `dash.page_registry`) and clicking it navigates correctly

- [ ] **Step 4: Commit**

```bash
git add pages/ai_footprint.py
git commit -m "feat: add AI Footprint page"
```

---

### Task 8: Footer citation

**Files:**
- Modify: `app.py`

**Interfaces:**
- Consumes: nothing
- Produces: nothing later depends on

- [ ] **Step 1: Add a citation paragraph to the footer**

In `app.py`, inside the `html.Footer` children list, after the existing second `html.P` (the GISTEMP/POWER one), add:

```python
                html.P([
                    "AI footprint estimates: modeled from MIT News, ",
                    html.A(
                        "\"Explained: Generative AI's environmental impact\"",
                        href="https://news.mit.edu/2025/explained-generative-ai-environmental-impact-0117",
                        target="_blank",
                    ),
                    " (Jan 2025), cross-checked for plausibility against the ",
                    html.A(
                        "ClimateAligned AI Footprint Calculator",
                        href="https://www.climatealigned.co/tools/ai-footprint-calculator",
                        target="_blank",
                    ),
                    " methodology. Not measured data — see the AI Footprint page for the full caveat.",
                ]),
```

- [ ] **Step 2: Manually verify**

Run: `python app.py`, open any page in a browser, scroll to the footer.
Expected: the new citation paragraph is visible with two working links.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "docs: cite AI footprint data sources in footer"
```

---

### Task 9: Full-suite verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `pytest tests/ -v`
Expected: All tests pass, including the network-dependent `test_capitals.py::test_capitals_covers_every_country_in_the_live_co2_dataset` test (requires internet — this is the one pre-existing test in the suite that does).

- [ ] **Step 2: Re-run the manual browser walkthrough from Task 7, Step 3, once more end-to-end**

This catches any regression introduced by Task 8's footer edit (e.g. a stray unclosed tag breaking every page, not just `/ai-footprint`).

- [ ] **Step 3: Verify the edge cases from the spec explicitly**

- Set "Queries per day" to `0` — KPI cards should show `0.0 Wh` / `0.0 g CO2e` / `0 mL`, not an error.
- Clear the prompt textarea entirely after having typed something — chart should revert to the dropdown's use case, not stay stuck on the last typed bucket.
- Pick a country and confirm the per-capita chart shows a real percentage (not "No data") for a country with recent CO2 data, e.g. a major emitter.

Expected: no crashes, no Dash error overlay, in any of the three cases.
