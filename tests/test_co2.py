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
