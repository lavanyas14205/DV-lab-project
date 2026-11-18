"""Five chart functions for the three research questions (see CLAUDE.md).

Every function takes `year` as a parameter so it plugs directly into a Dash
callback. None of these functions clean data themselves — they assume
data.py has already filtered aggregates, capped GDP, etc.
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import data


# --- Q1: Has global CO2 growth slowed since 2000? -------------------------

def emissions_temperature_line(co2_all, temperature, year):
    """Dual-axis line: global CO2 emissions vs GISTEMP anomaly, 1990-latest.

    Uses the "World" aggregate row deliberately — this is the one chart
    where the aggregate IS the subject, not something to filter out.
    """
    world = co2_all[co2_all["country"] == "World"]
    world = world[world["year"] >= data.DEFAULT_YEAR_RANGE[0]]
    temp = temperature[temperature["year"] >= data.DEFAULT_YEAR_RANGE[0]]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=world["year"], y=world["co2"], name="Global CO2 (Mt)"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=temp["year"], y=temp["temperature_anomaly"],
            name="Temperature anomaly (°C, observed)",
        ),
        secondary_y=True,
    )
    fig.add_vline(x=year, line_dash="dot", line_color="gray")
    fig.update_yaxes(title_text="CO2 emissions (Mt)", secondary_y=False)
    fig.update_yaxes(title_text="Temperature anomaly (°C)", secondary_y=True)
    fig.update_layout(
        title="Global CO2 emissions vs observed temperature anomaly",
        xaxis_title="Year",
    )
    return fig


def co2_growth_rate_bar(co2_all, year):
    """Year-over-year global CO2 growth rate, highlighting the selected year."""
    world = co2_all[co2_all["country"] == "World"]
    world = world[world["year"] >= data.DEFAULT_YEAR_RANGE[0]]

    colors = ["crimson" if y == year else "steelblue" for y in world["year"]]
    fig = go.Figure(
        go.Bar(x=world["year"], y=world["co2_growth_prct"], marker_color=colors)
    )
    fig.update_layout(
        title="Global CO2 growth rate by year",
        xaxis_title="Year",
        yaxis_title="Growth vs previous year (%)",
    )
    return fig


# --- Q2: Who emits most in total, versus per person? -----------------------

def emissions_choropleth(co2_countries, year, metric="total"):
    """Choropleth of country emissions for one year.

    metric="total" uses co2 (Mt); metric="per_capita" uses co2_per_capita
    and additionally excludes countries under 1M population (rule 6).
    """
    frame = co2_countries[co2_countries["year"] == year]
    if metric == "per_capita":
        frame = data.filter_min_population(frame)
        color_col, title = "co2_per_capita", f"CO2 per capita, {year} (t/person)"
    else:
        color_col, title = "co2", f"Total CO2 emissions, {year} (Mt)"

    fig = px.choropleth(
        frame,
        locations="iso_code",
        color=color_col,
        hover_name="country",
        color_continuous_scale="OrRd",
        title=title,
    )
    return fig


def top_emitters_paired_bar(co2_countries, year, top_n=15):
    """Paired horizontal bars: top emitters by total vs by per-capita.

    The gap between these two rankings is the dataset's clearest insight.
    """
    frame = co2_countries[co2_countries["year"] == year]

    total = frame.nlargest(top_n, "co2").sort_values("co2")
    per_capita_frame = data.filter_min_population(frame)
    per_capita = per_capita_frame.nlargest(top_n, "co2_per_capita").sort_values(
        "co2_per_capita"
    )

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=(f"Top {top_n} by total CO2 (Mt)", f"Top {top_n} by CO2 per capita (t)"),
    )
    fig.add_trace(
        go.Bar(x=total["co2"], y=total["country"], orientation="h", name="Total"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Bar(
            x=per_capita["co2_per_capita"], y=per_capita["country"],
            orientation="h", name="Per capita",
        ),
        row=1, col=2,
    )
    fig.update_layout(
        title=f"Total vs per-capita emissions leaders, {year}", showlegend=False
    )
    return fig


# --- Q3: Does higher GDP still mean higher emissions per person? -----------

def gdp_emissions_bubble(co2_countries, year):
    """Bubble scatter: GDP per capita (log x) vs CO2 per capita, sized by population.

    Capped at data.GDP_MAX_YEAR (rule 2) — GDP is not reported after that.
    """
    chart_year = min(year, data.GDP_MAX_YEAR)
    frame = co2_countries[co2_countries["year"] == chart_year].copy()
    frame = frame.dropna(subset=["gdp", "population", "co2_per_capita"])
    frame["gdp_per_capita"] = frame["gdp"] / frame["population"]

    fig = px.scatter(
        frame,
        x="gdp_per_capita",
        y="co2_per_capita",
        size="population",
        color="continent" if "continent" in frame.columns else None,
        hover_name="country",
        log_x=True,
        title=(
            f"GDP per capita vs CO2 per capita, {chart_year}"
            + (" (capped at 2022 — GDP not reported after)" if year > data.GDP_MAX_YEAR else "")
        ),
    )
    fig.update_layout(xaxis_title="GDP per capita (log scale)", yaxis_title="CO2 per capita (t)")
    return fig
