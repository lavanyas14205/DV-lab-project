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


# ---------------------------------------------------------------------------
# Everyday-equivalent and electricity-grid helpers (used by the AI Footprint
# page to explain the numbers in plain terms). The constants below are rough,
# widely quoted reference values -- they make a number *relatable*, they are
# not precise measurements.
# ---------------------------------------------------------------------------
LED_BULB_WATTS = 10          # a typical LED bulb
PHONE_CHARGE_WH = 12         # one full smartphone charge
CAR_G_CO2_PER_KM = 250       # average petrol car (~400 g/mile, US EPA)
TREE_G_CO2_PER_DAY = 60      # a mature tree absorbs ~22 kg CO2 per year
GLASS_ML = 250               # one glass of water

# Carbon intensity (g CO2 per kWh) used by the "greener grid" scenario.
# Wind/solar/hydro are not zero over their life-cycle (building the plant),
# so 100% renewable is ~30 g/kWh, not 0. FALLBACK_FOSSIL_G_PER_KWH is used
# only when a country is already ~100% renewable, so no fossil intensity
# can be inferred from its own data.
RENEWABLE_G_PER_KWH = 30
FALLBACK_FOSSIL_G_PER_KWH = 650


def equivalents(energy_wh: float, co2_g: float, water_ml: float) -> dict:
    """Translate raw energy / carbon / water totals into everyday units."""
    return {
        "led_hours": energy_wh / LED_BULB_WATTS,
        "phone_charges": energy_wh / PHONE_CHARGE_WH,
        "car_metres": co2_g / CAR_G_CO2_PER_KM * 1000,
        "tree_days": co2_g / TREE_G_CO2_PER_DAY,
        "water_glasses": water_ml / GLASS_ML,
    }


def grid_co2_g(energy_wh: float, intensity_g_per_kwh: float) -> float:
    """CO2 (grams) of using `energy_wh` on a grid with the given carbon intensity."""
    return energy_wh / 1000 * intensity_g_per_kwh


def scenario_intensity(current_intensity: float, current_renewable_pct: float, target_renewable_pct: float) -> float:
    """Carbon intensity if the country's electricity were `target_renewable_pct`
    renewable. The country's own non-renewable intensity is inferred from its
    current intensity and renewable share, so the scenario starts exactly at
    today's real value.
    """
    r_now = min(max(current_renewable_pct, 0), 100) / 100
    r_new = min(max(target_renewable_pct, 0), 100) / 100
    if r_now >= 0.99:
        fossil = FALLBACK_FOSSIL_G_PER_KWH
    else:
        fossil = max((current_intensity - RENEWABLE_G_PER_KWH * r_now) / (1 - r_now), 0)
    return fossil * (1 - r_new) + RENEWABLE_G_PER_KWH * r_new


def grid_snapshot(countries: pd.DataFrame, energy: pd.DataFrame, year: int, min_population: float = 1_000_000) -> pd.DataFrame:
    """One row per country with its grid carbon intensity and renewable share
    for `year`. `countries` is the aggregate-filtered frame (cleaning rule 1);
    countries under `min_population` are dropped so tiny territories with
    placeholder values (e.g. exactly 1000 g/kWh) do not top the ranking.
    """
    wanted = energy[energy["year"] == year][
        ["country", "iso_code", "carbon_intensity_elec", "renewables_share_elec"]
    ]
    wanted = wanted[wanted["iso_code"].isin(countries["iso_code"].unique())]
    pop = countries[countries["year"] == year][["iso_code", "population"]]
    merged = wanted.merge(pop, on="iso_code", how="inner")
    merged = merged[merged["population"] >= min_population]
    merged = merged.dropna(subset=["carbon_intensity_elec", "renewables_share_elec"])
    # An exact 0 g/kWh is a reporting artefact (even hydro/wind have
    # life-cycle emissions) and would make "X times cleaner" meaningless.
    return merged[merged["carbon_intensity_elec"] > 0].reset_index(drop=True)
