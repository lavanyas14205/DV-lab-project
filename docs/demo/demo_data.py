"""A tiny, hand-picked dataset for the Phase 3 "why Plotly" demo.

Deliberately small (8 countries, 10 years) and hardcoded — no network call —
so the live demo works offline, in front of the teacher, with no risk of a
slow or failed download. Numbers are rounded, illustrative approximations of
real-world 2023-ish figures, shaped exactly like the real, much bigger OWID
CO2 file used in the actual dashboard (data/co2.py):

    country, co2_per_capita, gdp_per_capita, population, continent

This is the same shape of table the real Q3 chart
(prototype_charts.gdp_emissions_bubble) plots — just 8 rows instead of ~190.
"""

import pandas as pd

# --- Dataset 1: one snapshot year, 8 countries (mirrors the real Q3 chart) --
GDP_CO2_SNAPSHOT = pd.DataFrame([
    {"country": "United States", "continent": "North America", "co2_per_capita": 14.9, "gdp_per_capita": 76000, "population_millions": 335},
    {"country": "China",          "continent": "Asia",          "co2_per_capita": 8.0,  "gdp_per_capita": 12700, "population_millions": 1412},
    {"country": "India",          "continent": "Asia",          "co2_per_capita": 1.9,  "gdp_per_capita": 2400,  "population_millions": 1428},
    {"country": "Germany",        "continent": "Europe",        "co2_per_capita": 8.1,  "gdp_per_capita": 48700, "population_millions": 84},
    {"country": "Brazil",         "continent": "South America", "co2_per_capita": 2.2,  "gdp_per_capita": 8900,  "population_millions": 216},
    {"country": "Nigeria",        "continent": "Africa",        "co2_per_capita": 0.6,  "gdp_per_capita": 2200,  "population_millions": 223},
    {"country": "Australia",      "continent": "Oceania",       "co2_per_capita": 15.3, "gdp_per_capita": 64500, "population_millions": 26},
    {"country": "Japan",          "continent": "Asia",          "co2_per_capita": 8.5,  "gdp_per_capita": 33800, "population_millions": 124},
])

# --- Dataset 2: one series, 10 years (mirrors the real Q1 line chart) ------
WORLD_CO2_TREND = pd.DataFrame({
    "year": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
    "co2_mt": [35400, 35500, 36000, 36700, 37000, 34800, 36400, 37000, 37400, 37800],
})
