"""Country Climate Profile page: one country's headline numbers and trends."""

import dash
from dash import Input, Output, dcc, html

import analysis
import country_profile_charts as charts
import data
import state
from data.co2 import GDP_MAX_YEAR
from data.energy import ENERGY_MAX_YEAR, RENEWABLE_SHARE_COLUMN

dash.register_page(__name__, path="/country", name="Country Profile", order=5)

_COUNTRY_OPTIONS = sorted(state.loaded.co2_countries["country"].unique())
_LATEST_YEAR = int(state.loaded.co2_countries["year"].max())
_DEFAULT_COUNTRY = analysis.top_emitter(state.loaded.co2_countries, _LATEST_YEAR)

# The source frame is immutable after startup load, so the derived
# gdp_per_capita frame is computed once here rather than on every callback
# invocation (with_gdp_per_capita copies the whole ~42,000-row frame).
_CO2_WITH_GDP = analysis.with_gdp_per_capita(state.loaded.co2_countries)


def layout():
    return html.Div([
        html.H2("Country Climate Profile"),
        html.Label("Country:", htmlFor="country-profile-dropdown"),
        dcc.Dropdown(
            id="country-profile-dropdown",
            options=[{"label": c, "value": c} for c in _COUNTRY_OPTIONS],
            value=_DEFAULT_COUNTRY,
            clearable=False,
        ),
        html.Div(
            id="country-profile-kpis",
            className="kpi-row",
        ),
        dcc.Graph(id="country-profile-trends"),
    ])


def _kpi_card(label, value_text):
    return html.Div(
        className="kpi-card",
        children=[
            html.Div(label, className="kpi-label"),
            html.Div(value_text, className="kpi-value"),
        ],
    )


@dash.callback(
    Output("country-profile-kpis", "children"),
    Output("country-profile-trends", "figure"),
    Input("country-profile-dropdown", "value"),
)
def update_country_profile(country):
    min_year = data.DEFAULT_YEAR_RANGE[0]

    population_series = analysis.country_series(
        state.loaded.co2_countries, country, "population", min_year=min_year
    )
    co2_series = analysis.country_series(state.loaded.co2_countries, country, "co2", min_year=min_year)
    co2_pc_series = analysis.country_series(
        state.loaded.co2_countries, country, "co2_per_capita", min_year=min_year
    )
    gdp_pc_series = analysis.country_series(
        _CO2_WITH_GDP, country, "gdp_per_capita", min_year=min_year, max_year=GDP_MAX_YEAR
    )
    renew_series = analysis.country_series(
        state.loaded.energy, country, RENEWABLE_SHARE_COLUMN, min_year=min_year, max_year=ENERGY_MAX_YEAR
    )

    kpis = []
    pop_latest = analysis.latest_value(population_series)
    kpis.append(_kpi_card("Population", f"{pop_latest[1]:,.0f}" if pop_latest else "No data"))
    gdp_latest = analysis.latest_value(gdp_pc_series)
    kpis.append(
        _kpi_card("GDP / person", f"${gdp_latest[1]:,.0f} ({gdp_latest[0]})" if gdp_latest else "No data")
    )
    co2_latest = analysis.latest_value(co2_series)
    kpis.append(
        _kpi_card("CO2 emissions", f"{co2_latest[1]:,.0f} Mt ({co2_latest[0]})" if co2_latest else "No data")
    )
    co2_pc_latest = analysis.latest_value(co2_pc_series)
    kpis.append(
        _kpi_card("CO2 / person", f"{co2_pc_latest[1]:.1f} t ({co2_pc_latest[0]})" if co2_pc_latest else "No data")
    )
    renew_latest = analysis.latest_value(renew_series)
    kpis.append(
        _kpi_card(
            "Renewable electricity",
            f"{renew_latest[1]:.0f}% ({renew_latest[0]})" if renew_latest else "No data",
        )
    )

    fig = charts.country_trend_sparklines({
        "CO2 emissions (Mt)": co2_series,
        "CO2 per person (t)": co2_pc_series,
        f"GDP per person ($, to {GDP_MAX_YEAR})": gdp_pc_series,
        "Renewable electricity (%)": renew_series,
    })
    return kpis, fig
