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
