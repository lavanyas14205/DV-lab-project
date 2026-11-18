"""Q4 chart: renewable electricity adoption vs solar/wind potential."""

import numpy as np
import pandas as pd
import plotly.express as px

from data.energy import RENEWABLE_SHARE_COLUMN

POTENTIAL_COLUMNS = {
    "solar": "solar_kwh_per_m2_day",
    "wind": "wind_speed_ms",
}


def trend_residuals(x: pd.Series, y: pd.Series) -> pd.Series:
    """Vertical distance of each point from a best-fit line through (x, y)."""
    slope, intercept = np.polyfit(x, y, 1)
    predicted = slope * x + intercept
    return y - predicted


def top_extremes(countries: pd.Series, residuals: pd.Series, n: int = 3) -> list:
    """The n countries furthest below and furthest above the trend line, by name."""
    ranked = residuals.sort_values()
    below = list(countries.loc[ranked.index[:n]])
    above = list(countries.loc[ranked.index[-n:]])
    return below + above


POTENTIAL_UNITS = {"solar": "kWh/m2/day", "wind": "m/s"}


def _prepare(energy_df: pd.DataFrame, climatology_df: pd.DataFrame, potential: str):
    """Shared merge + residual computation used by both the bubble chart and
    outlier_details, so the two never drift out of sync on filtering logic."""
    potential_col = POTENTIAL_COLUMNS[potential]
    merged = energy_df.merge(climatology_df, on="iso_code", how="inner")
    merged = merged.dropna(subset=[potential_col, RENEWABLE_SHARE_COLUMN, "population"])
    merged["residual"] = trend_residuals(merged[potential_col], merged[RENEWABLE_SHARE_COLUMN])
    return merged, potential_col


def renewable_potential_vs_adoption_bubble(energy_df: pd.DataFrame, climatology_df: pd.DataFrame, potential: str = "solar"):
    """Bubble scatter: x = solar/wind potential, y = renewable electricity
    share, sized by population. The 3 countries furthest above and below a
    fitted trend line are labeled — the gap between natural potential and
    actual adoption is the point of this chart.
    """
    merged, potential_col = _prepare(energy_df, climatology_df, potential)

    labeled_countries = set(top_extremes(merged["country"], merged["residual"]))
    merged["label"] = merged["country"].where(merged["country"].isin(labeled_countries), "")

    fig = px.scatter(
        merged,
        x=potential_col,
        y=RENEWABLE_SHARE_COLUMN,
        size="population",
        text="label",
        hover_name="country",
        title=f"Renewable electricity share vs {potential} potential",
    )
    fig.update_traces(textposition="top center")
    fig.update_layout(
        xaxis_title=f"{potential.title()} potential ({POTENTIAL_UNITS[potential]})",
        yaxis_title="Renewable share of electricity (%)",
    )
    return fig


def outlier_details(energy_df: pd.DataFrame, climatology_df: pd.DataFrame, potential: str = "solar", n: int = 3) -> dict:
    """Countries furthest above/below the fitted adoption-vs-potential trend,
    each as a dict with country, potential value, renewable share, and
    residual — the data behind the Q4 "Adoption Leaders" /
    "Potential Under-Utilisers" callouts. Not a causal claim: a country
    above the trend has relatively high adoption *for its measured
    potential*, nothing more.
    """
    merged, potential_col = _prepare(energy_df, climatology_df, potential)
    ranked = merged.sort_values("residual")
    columns = ["country", potential_col, RENEWABLE_SHARE_COLUMN, "residual"]
    under_utilisers = ranked.head(n)[columns].to_dict("records")
    leaders = ranked.tail(n)[columns].iloc[::-1].to_dict("records")
    return {"leaders": leaders, "under_utilisers": under_utilisers}
