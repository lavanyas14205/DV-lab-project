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
