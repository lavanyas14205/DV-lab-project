"""Pure analytical helpers layered on top of the base charts in
prototype_charts.py. Kept separate and pure so they're unit-testable
without touching chart/plotting code.
"""

import pandas as pd


def rolling_growth_average(world_co2: pd.DataFrame, window: int = 5) -> pd.Series:
    """Rolling mean of co2_growth_prct, indexed the same as world_co2."""
    return world_co2["co2_growth_prct"].rolling(window=window, min_periods=1).mean()


def growth_period_means(world_co2: pd.DataFrame, early_range: tuple, late_range: tuple) -> tuple:
    """Mean growth rate over two year ranges, e.g. (1990, 1999) vs (2015, 2024)."""
    early = world_co2[world_co2["year"].between(*early_range)]["co2_growth_prct"].mean()
    late = world_co2[world_co2["year"].between(*late_range)]["co2_growth_prct"].mean()
    return early, late


def country_series(
    df: pd.DataFrame,
    country: str,
    value_column: str,
    min_year: int | None = None,
    max_year: int | None = None,
) -> pd.DataFrame:
    """One country's (year, value) trend for one column, NaNs dropped.

    Bounds are optional — e.g. GDP capped at data.co2.GDP_MAX_YEAR (rule 2),
    or the dashboard's default 1990 start (rule 4). Always returns exactly
    ["year", "value"] columns so callers don't need to know the source
    column name.
    """
    frame = df[df["country"] == country].dropna(subset=[value_column])
    if min_year is not None:
        frame = frame[frame["year"] >= min_year]
    if max_year is not None:
        frame = frame[frame["year"] <= max_year]
    frame = frame.sort_values("year")
    return frame[["year", value_column]].rename(columns={value_column: "value"}).reset_index(drop=True)


def latest_value(series: pd.DataFrame) -> tuple[int, float] | None:
    """(year, value) of the last row of a country_series() result, or None."""
    if series.empty:
        return None
    row = series.iloc[-1]
    return int(row["year"]), float(row["value"])


def with_gdp_per_capita(co2_countries: pd.DataFrame) -> pd.DataFrame:
    """co2_countries plus a derived gdp_per_capita column.

    NaN where gdp or population is missing — never filled with 0 (a missing
    GDP is not a zero GDP). Same derivation prototype_charts.gdp_emissions_bubble
    uses inline; factored out here so it's reusable and testable on its own.
    """
    out = co2_countries.copy()
    out["gdp_per_capita"] = out["gdp"] / out["population"]
    return out


def value_at_year(df: pd.DataFrame, year: int, column: str) -> float | None:
    """Value of `column` at `year` in a single-row-per-year frame.

    Used for global aggregates (the "World" row of co2_all/energy, or
    state.loaded.temperature, which has no country dimension at all).
    Returns None rather than a fabricated 0 when the year is missing or the
    value is NaN.
    """
    matches = df[df["year"] == year]
    if matches.empty:
        return None
    value = matches.iloc[0][column]
    return None if pd.isna(value) else float(value)


def percent_change(from_value: float | None, to_value: float | None) -> float | None:
    """(to - from) / from * 100. None if either value or the baseline is missing/zero."""
    if from_value is None or to_value is None or from_value == 0:
        return None
    return (to_value - from_value) / from_value * 100


def absolute_change(from_value: float | None, to_value: float | None) -> float | None:
    """to - from. None if either value is missing (e.g. temperature anomaly,
    where a percent change is meaningless near a zero baseline)."""
    if from_value is None or to_value is None:
        return None
    return to_value - from_value


def top_emitter(co2_countries: pd.DataFrame, year: int) -> str | None:
    """Name of the country with the highest co2 in the given year, or None
    if there's no country-level data for that year.

    Shared by pages/country_profile.py (default country) and
    pages/overview.py (headline "top emitter" line), which both used to do
    this `.nlargest(1, "co2").iloc[0]` idiom independently, with no guard
    against an empty slice.
    """
    year_rows = co2_countries[co2_countries["year"] == year]
    if year_rows.empty:
        return None
    return year_rows.nlargest(1, "co2").iloc[0]["country"]
