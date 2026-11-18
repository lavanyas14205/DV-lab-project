import pandas as pd
import pytest

from analysis import absolute_change, country_series, growth_period_means, latest_value, percent_change, rolling_growth_average, top_emitter, value_at_year, with_gdp_per_capita


def test_rolling_growth_average_smooths_year_to_year_noise():
    world = pd.DataFrame({"year": [2000, 2001, 2002], "co2_growth_prct": [1.0, 3.0, 2.0]})

    result = rolling_growth_average(world, window=3)

    assert result.iloc[-1] == 2.0  # mean of 1.0, 3.0, 2.0


def test_growth_period_means_compares_two_year_ranges():
    world = pd.DataFrame(
        {
            "year": [1990, 1991, 2015, 2016],
            "co2_growth_prct": [2.0, 4.0, 1.0, 1.0],
        }
    )

    early, late = growth_period_means(world, (1990, 1991), (2015, 2016))

    assert early == 3.0
    assert late == 1.0


def test_country_series_drops_nan_and_sorts_by_year():
    df = pd.DataFrame(
        {
            "country": ["India", "India", "India", "China"],
            "year": [2002, 2000, 2001, 2000],
            "co2": [5.0, 3.0, None, 9.0],
        }
    )

    result = country_series(df, "India", "co2")

    assert list(result["year"]) == [2000, 2002]
    assert list(result["value"]) == [3.0, 5.0]


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


def test_with_gdp_per_capita_adds_derived_column():
    df = pd.DataFrame({"country": ["India", "Palau"], "gdp": [3_000_000, None], "population": [1_400_000_000, 18_000]})

    result = with_gdp_per_capita(df)

    assert result.loc[0, "gdp_per_capita"] == 3_000_000 / 1_400_000_000
    assert pd.isna(result.loc[1, "gdp_per_capita"])
    assert "gdp" in df.columns  # original frame untouched


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


def test_top_emitter_returns_the_highest_co2_country_for_that_year():
    df = pd.DataFrame(
        {
            "country": ["India", "China", "USA", "China"],
            "year": [2020, 2020, 2020, 2019],
            "co2": [2500.0, 9000.0, 4500.0, 8000.0],
        }
    )

    assert top_emitter(df, 2020) == "China"


def test_top_emitter_returns_none_when_year_has_no_data():
    df = pd.DataFrame({"country": ["India"], "year": [2020], "co2": [2500.0]})

    assert top_emitter(df, 1999) is None
