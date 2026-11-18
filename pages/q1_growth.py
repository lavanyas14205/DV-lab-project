"""Q1 page: has global CO2 growth slowed since 2000?"""

import dash
from dash import Input, Output, dcc, html

import analysis
import data
import prototype_charts as charts
import state

dash.register_page(__name__, path="/q1", name="Growth", order=1)

_MIN_YEAR = data.DEFAULT_YEAR_RANGE[0]
_MAX_YEAR = int(state.loaded.co2_countries["year"].max())


def layout():
    return html.Div([
        html.H2("Has global CO2 growth slowed since 2000?"),
        html.Label("Year:", htmlFor="q1-year-slider"),
        dcc.Slider(
            id="q1-year-slider",
            min=_MIN_YEAR,
            max=_MAX_YEAR,
            step=1,
            value=_MAX_YEAR,
            marks={y: str(y) for y in range(_MIN_YEAR, _MAX_YEAR + 1, 5)},
            tooltip={"placement": "bottom", "always_visible": True},
        ),
        html.Div(
            style={"display": "flex", "gap": "20px", "flexWrap": "wrap"},
            children=[
                dcc.Graph(id="q1-line", style={"flex": "1", "minWidth": "450px"}),
                dcc.Graph(id="q1-growth-bar", style={"flex": "1", "minWidth": "450px"}),
            ],
        ),
    ])


@dash.callback(
    Output("q1-line", "figure"),
    Output("q1-growth-bar", "figure"),
    Input("q1-year-slider", "value"),
)
def update_q1(year):
    line_fig = charts.emissions_temperature_line(state.loaded.co2_all, state.loaded.temperature, year)
    bar_fig = charts.co2_growth_rate_bar(state.loaded.co2_all, year)

    world = state.loaded.co2_all[state.loaded.co2_all["country"] == "World"]
    world = world[world["year"] >= data.DEFAULT_YEAR_RANGE[0]]
    rolling = analysis.rolling_growth_average(world)
    bar_fig.add_scatter(x=world["year"], y=rolling, mode="lines", name="5-year rolling average")

    early, late = analysis.growth_period_means(world, (1990, 1999), (2015, 2024))
    bar_fig.add_annotation(
        xref="paper", yref="paper", x=0.02, y=0.98, showarrow=False, align="left",
        text=f"Mean growth 1990-1999: {early:.2f}%/yr<br>Mean growth 2015-2024: {late:.2f}%/yr",
        bgcolor="white", bordercolor="gray",
    )
    return line_fig, bar_fig
