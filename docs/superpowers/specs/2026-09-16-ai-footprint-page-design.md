# AI Footprint Page — Design Spec

Date: 2026-09-16
Status: approved by user, pending implementation plan

## Context

The dashboard currently answers four research questions (Q1-Q4) plus two
utility pages (Country Profile, Compare Years), all built on OWID CO2, OWID
Energy, GISTEMP, and a cached NASA POWER climatology — see `CLAUDE.md`.

The user's sister and her lecturer asked what makes this project distinctive
compared to other "weather/climate dashboard" coursework. The idea: add a
page estimating the water/energy/carbon footprint of using an AI model
(ChatGPT, Claude, Gemini, Grok), and — this is the differentiator — tie that
estimate back into the real climate data already in the app, rather than
building a standalone calculator.

Research inputs reviewed before this design:

- MIT News, ["Explained: Generative AI's environmental
  impact"](https://news.mit.edu/2025/explained-generative-ai-environmental-impact-0117)
  (Jan 2025): a ChatGPT query uses ~5x the electricity of a basic web search;
  training GPT-3 took 1,287 MWh; data centers need ~2L water per kWh for
  cooling; researchers stress there is **no standardized, comprehensive
  measurement** of per-query cost — any figure is modeled, not measured.
- [ClimateAligned's AI Footprint
  Calculator](https://www.climatealigned.co/tools/ai-footprint-calculator):
  a live reference tool with per-model, per-use-case estimates (energy Wh,
  carbon gCO2e, water mL), methodology citing Google's 2024 production
  measurements and EPA eGRID 2022/Green-e 2024 grid data. Useful as a
  cross-check for plausible orders of magnitude, but its numbers are not
  copied directly — this project sources its own reference table (see Data
  layer, below) so the methodology is independently defensible in a viva.
- A ChatGPT conversation shared by the user's sister was not retrievable
  (share link failed to render content via both a fetch tool and a live
  browser tab) — not used as an input to this design.

## Goals

- Add an "AI Footprint" utility page: pick or type a prompt, see the
  estimated energy/CO2/water cost, compared across models, scaled to a
  usage habit, and contextualized against a real country's per-capita CO2.
- Keep the project's existing constraints intact: free tier only, no API
  keys, no live network calls from the running app.
- Make the estimate's nature (modeled from published studies, not measured)
  as explicit as the existing "modelled vs. measured" temperature rule
  already in `CLAUDE.md`.

## Non-goals

- Not a live call to any AI-footprint API or to the AI models themselves —
  same "no network code in the running app" rule as `data/climatology.py`.
- Not a precise per-token energy simulator. The reference table is a small,
  hand-curated set of model x use-case estimates, not a formula fit to
  token count.
- Not a country-level water or energy per-capita comparison — no source in
  this project has country-level domestic water-use data, so that leg of
  the comparison uses a global/regional benchmark instead, clearly labeled.

## Architecture overview

```
data/
  ai_footprint.csv        # NEW — curated reference table: model, use_case,
                           # energy_wh, co2_g, water_ml, word_count_max, source
  ai_footprint.py         # NEW — loader, added to LoadedData/load_all()
ai_footprint_analysis.py  # NEW — bucket_prompt(), per_capita_share()
ai_footprint_charts.py    # NEW — model-comparison bar, per-capita comparison chart
pages/
  ai_footprint.py         # NEW — page at /ai-footprint, order=7
tests/
  test_ai_footprint.py    # NEW
```

## Data layer

### Reference table (`data/ai_footprint.csv`)

Columns: `model, use_case, energy_wh, co2_g, water_ml, word_count_max, source`.

Four models (Claude, ChatGPT, Gemini, Grok) x four use cases (Simple Q&A,
Email/Summary, Document Review, Coding/Agent Session) = 16 rows. Values are
hand-derived from the MIT News figures (the "~5x a web search" ratio, the
2L-water-per-kWh cooling ratio) and cross-checked for plausibility against
ClimateAligned's displayed orders of magnitude, not copied from them. Each
row cites its derivation in `source`. `word_count_max` gives the upper word
count for that use case, used by `bucket_prompt()` below (e.g. Simple Q&A
<= 30 words, Email/Summary <= 150, Document Review <= unbounded).

This mirrors the existing `data/capitals.csv` and `data/power_climatology.csv`
pattern: a small, static, hand-authored or hand-derived CSV, committed to
the repo, with its provenance documented in a header comment.

### Loader (`data/ai_footprint.py`)

```python
def load_ai_footprint_data(path: str = AI_FOOTPRINT_PATH) -> pd.DataFrame:
    return pd.read_csv(path)
```

Added to `LoadedData` as `ai_footprint: pd.DataFrame` and wired into
`load_all()`, same as every other frame in `data/__init__.py`.

### Analysis helpers (`ai_footprint_analysis.py`)

Two pure functions, following the existing `analysis.py` style (pure,
unit-tested, no Dash/IO dependency):

- `bucket_prompt(text: str, footprint: pd.DataFrame) -> str`: counts words
  in `text`, returns the matching `use_case` by comparing against
  `word_count_max` per use case. Empty/whitespace-only text returns `None`
  (caller falls back to the dropdown's selected use case).
- `per_capita_share(total_co2_g: float, country_annual_co2_per_capita_t: float | None) -> float | None`:
  returns the percentage `total_co2_g` represents of one person's annual
  CO2 footprint in the selected country. Returns `None` if the country's
  per-capita value is missing (mirrors `analysis.latest_value`'s
  `None`-on-missing-data convention already used elsewhere in the app).

Kept as a separate module rather than added to `analysis.py` to keep that
file focused on the existing Q1/country/compare-years helpers — same
reasoning as why Q4 got its own `q4_charts.py` instead of extending
`prototype_charts.py`.

## Page (`pages/ai_footprint.py`)

`dash.register_page(__name__, path="/ai-footprint", name="AI Footprint", order=7)`.

**Controls:**
- Model checklist/selector (all four shown by default for comparison)
- Use-case dropdown (default control)
- Optional prompt textarea — when non-empty, overrides the dropdown via
  `bucket_prompt()`
- Queries-per-day numeric input + 5-day/7-day week toggle (mirrors
  ClimateAligned's usage-scaling control)
- Country dropdown, reusing the same `state.loaded.co2_countries` country
  list as `pages/country_profile.py`

**Outputs:**
1. Grouped bar chart (`ai_footprint_charts.model_comparison_bar`): for the
   selected use case, one group of bars per metric (energy/CO2/water),
   one bar per model.
2. Per-capita comparison chart/KPI
   (`ai_footprint_charts.per_capita_comparison`): projects the selected
   model's footprint across the queries-per-day x days-per-week x one
   month, and shows it as a percentage of the selected country's latest
   `co2_per_capita` value (already available in `state.loaded.co2_countries`
   — no new data source needed for this leg). If the country's latest
   `co2_per_capita` is missing, show "No data" (same convention as
   `country_profile.py`'s KPI cards) rather than erroring.
3. CSV download of `data/ai_footprint.csv`, via `dcc.Download`, same
   `dcc.send_data_frame` pattern as `pages/q4_renewables.py`.

**Disclosure banner:** a visible, permanent note on the page (not
dismissible) stating these are modeled estimates derived from published
third-party studies, not real-time measurements — actual per-query cost
varies by hardware, region, and model version, and the water comparison
uses a global average, not a country-specific figure. This
follows the same spirit as the existing "temperature_change_from_co2 is
modelled, not measured" rule in `CLAUDE.md`.

## App shell changes

- `data/__init__.py`: add `ai_footprint` to `LoadedData` and `load_all()`.
- `app.py`: no changes needed — nav is generated from `dash.page_registry`,
  so the new page appears automatically. Footer gets one more citation line
  for the AI-footprint reference sources (MIT News, ClimateAligned
  methodology reference).

## Testing (`tests/test_ai_footprint.py`)

- `bucket_prompt`: boundary word counts land in the expected use case
  (e.g. exactly `word_count_max` words still falls in that bucket, one word
  over falls into the next); empty string returns `None`.
- `per_capita_share`: normal case, `None` per-capita input, zero CO2 input.
- Data-integrity test on `data/ai_footprint.csv`: expected columns present,
  all four models x four use cases present (16 rows), no missing values in
  `energy_wh`/`co2_g`/`water_ml`.
- Chart functions are verified in-browser, not unit-tested — consistent
  with how every other chart module in this project (`prototype_charts.py`,
  `q4_charts.py`, `country_profile_charts.py`) is verified.

## Error handling / edge cases

- Empty or all-whitespace prompt text: `bucket_prompt` returns `None`, page
  falls back to the dropdown's use case — never errors.
- Country with missing `co2_per_capita` for its latest year: per-capita
  comparison shows "No data", not a crash or a silently wrong 0%.
- Zero queries-per-day: projected totals are 0; per-capita percentage is 0%,
  not a division error.

## Deployment

No change to the existing Render deployment plan. No new runtime
dependencies — `data/ai_footprint.csv` is committed like the other static
CSVs, so the deployed app never needs any network access for this feature.
