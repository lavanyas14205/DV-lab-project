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
