"""Shared loading and cleaning for the Global Climate Trends dashboard.

Package layout: co2.py and gistemp.py hold source-specific loading and
cleaning; this file just orchestrates them behind load_all().
"""

from dataclasses import dataclass

import pandas as pd

from .climatology import CLIMATOLOGY_PATH, load_climatology_data
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
from .ai_footprint import AI_FOOTPRINT_PATH, load_ai_footprint_data
from .energy import ENERGY_URL, load_energy_data
from .gistemp import GISTEMP_URL, load_temperature_data, parse_gistemp

__all__ = [
    "CO2_URL", "GISTEMP_URL", "ENERGY_URL", "CLIMATOLOGY_PATH", "AI_FOOTPRINT_PATH", "DEFAULT_YEAR_RANGE", "GDP_MAX_YEAR",
    "MIN_POPULATION_FOR_PER_CAPITA", "SPARSE_EMISSIONS_COLUMNS",
    "MODELLED_TEMPERATURE_COLUMN", "cap_year", "filter_countries",
    "filter_min_population", "load_co2_data", "load_temperature_data",
    "load_energy_data", "load_climatology_data", "load_ai_footprint_data", "parse_gistemp", "LoadedData", "load_all",
]


@dataclass
class LoadedData:
    co2_all: pd.DataFrame
    co2_countries: pd.DataFrame
    temperature: pd.DataFrame
    energy: pd.DataFrame
    climatology: pd.DataFrame
    ai_footprint: pd.DataFrame


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
