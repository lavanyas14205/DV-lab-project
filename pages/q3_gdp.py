"""Q3 page: does higher GDP still mean higher emissions per person?"""

import io

import dash
from dash import Input, Output, dcc, html

import data
import prototype_charts as charts
import state

dash.register_page(__name__, path="/q3", name="GDP", order=3)

_MIN_YEAR = data.DEFAULT_YEAR_RANGE[0]
_MAX_YEAR = int(state.loaded.co2_countries["year"].max())
_COUNTRY_OPTIONS = sorted(state.loaded.co2_countries["country"].unique())


def layout():
    return html.Div([
        html.H2("Does higher GDP still mean higher emissions per person?"),
        html.Div(
            style={"display": "flex", "gap": "30px", "flexWrap": "wrap", "alignItems": "flex-end"},
            children=[
                html.Div(
                    style={"flex": "2", "minWidth": "300px"},
                    children=[
                        html.Label("Year:", htmlFor="q3-year-slider"),
                        dcc.Slider(
                            id="q3-year-slider", min=_MIN_YEAR, max=_MAX_YEAR, step=1, value=_MAX_YEAR,
                            marks={y: str(y) for y in range(_MIN_YEAR, _MAX_YEAR + 1, 5)},
                            tooltip={"placement": "bottom", "always_visible": True},
                        ),
                    ],
                ),
                html.Div(
                    style={"flex": "2", "minWidth": "250px"},
                    children=[
                        html.Label("Countries (optional filter):", htmlFor="q3-country-dropdown"),
                        dcc.Dropdown(
                            id="q3-country-dropdown",
                            options=[{"label": c, "value": c} for c in _COUNTRY_OPTIONS],
                            multi=True, placeholder="All countries",
                        ),
                    ],
                ),
                html.Div([
                    html.Button("Download filtered CSV", id="q3-download-button"),
                    dcc.Download(id="q3-download-csv"),
                ]),
            ],
        ),
        dcc.Graph(id="q3-bubble"),
    ])


def _filtered(selected_countries):
    countries = state.loaded.co2_countries
    if selected_countries:
        return countries[countries["country"].isin(selected_countries)]
    return countries


@dash.callback(
    Output("q3-bubble", "figure"),
    Input("q3-year-slider", "value"),
    Input("q3-country-dropdown", "value"),
)
def update_q3(year, selected_countries):
    return charts.gdp_emissions_bubble(_filtered(selected_countries), year)


@dash.callback(
    Output("q3-download-csv", "data"),
    Input("q3-download-button", "n_clicks"),
    Input("q3-year-slider", "value"),
    Input("q3-country-dropdown", "value"),
    prevent_initial_call=True,
)
def download_q3(n_clicks, year, selected_countries):
    if dash.callback_context.triggered_id != "q3-download-button":
        raise dash.exceptions.PreventUpdate
    frame = _filtered(selected_countries)
    frame = frame[frame["year"] == year]
    buffer = io.StringIO()
    frame.to_csv(buffer, index=False)
    return dict(content=buffer.getvalue(), filename=f"q3_gdp_{year}.csv")
