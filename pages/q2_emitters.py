"""Q2 page: who emits most in total, versus per person?"""

import io

import dash
from dash import Input, Output, dcc, html

import data
import prototype_charts as charts
import state

dash.register_page(__name__, path="/q2", name="Who Emits", order=2)

_MIN_YEAR = data.DEFAULT_YEAR_RANGE[0]
_MAX_YEAR = int(state.loaded.co2_countries["year"].max())
_COUNTRY_OPTIONS = sorted(state.loaded.co2_countries["country"].unique())


def layout():
    return html.Div([
        html.H2("Who emits most in total, versus per person?"),
        html.Div(
            style={"display": "flex", "gap": "30px", "flexWrap": "wrap", "alignItems": "flex-end"},
            children=[
                html.Div(
                    style={"flex": "2", "minWidth": "300px"},
                    children=[
                        html.Label("Year:", htmlFor="q2-year-slider"),
                        dcc.Slider(
                            id="q2-year-slider", min=_MIN_YEAR, max=_MAX_YEAR, step=1, value=_MAX_YEAR,
                            marks={y: str(y) for y in range(_MIN_YEAR, _MAX_YEAR + 1, 5)},
                            tooltip={"placement": "bottom", "always_visible": True},
                        ),
                    ],
                ),
                html.Div(
                    style={"flex": "2", "minWidth": "250px"},
                    children=[
                        html.Label("Countries (optional filter):", htmlFor="q2-country-dropdown"),
                        dcc.Dropdown(
                            id="q2-country-dropdown",
                            options=[{"label": c, "value": c} for c in _COUNTRY_OPTIONS],
                            multi=True, placeholder="All countries",
                        ),
                    ],
                ),
                html.Div(
                    style={"flex": "1", "minWidth": "180px"},
                    children=[
                        html.Label("Map metric:", htmlFor="q2-metric-toggle"),
                        dcc.RadioItems(
                            id="q2-metric-toggle",
                            options=[
                                {"label": "Total", "value": "total"},
                                {"label": "Per capita", "value": "per_capita"},
                            ],
                            value="total", inline=True,
                        ),
                    ],
                ),
                html.Div([
                    html.Button("Download filtered CSV", id="q2-download-button"),
                    dcc.Download(id="q2-download-csv"),
                ]),
            ],
        ),
        dcc.Graph(id="q2-choropleth"),
        dcc.Graph(id="q2-paired-bar"),
    ])


def _filtered(selected_countries):
    countries = state.loaded.co2_countries
    if selected_countries:
        return countries[countries["country"].isin(selected_countries)]
    return countries


@dash.callback(
    Output("q2-choropleth", "figure"),
    Output("q2-paired-bar", "figure"),
    Input("q2-year-slider", "value"),
    Input("q2-country-dropdown", "value"),
    Input("q2-metric-toggle", "value"),
)
def update_q2(year, selected_countries, metric):
    countries = _filtered(selected_countries)
    return (
        charts.emissions_choropleth(countries, year, metric=metric),
        charts.top_emitters_paired_bar(countries, year),
    )


@dash.callback(
    Output("q2-download-csv", "data"),
    Input("q2-download-button", "n_clicks"),
    Input("q2-year-slider", "value"),
    Input("q2-country-dropdown", "value"),
    prevent_initial_call=True,
)
def download_q2(n_clicks, year, selected_countries):
    if dash.callback_context.triggered_id != "q2-download-button":
        raise dash.exceptions.PreventUpdate
    frame = _filtered(selected_countries)
    frame = frame[frame["year"] == year]
    buffer = io.StringIO()
    frame.to_csv(buffer, index=False)
    return dict(content=buffer.getvalue(), filename=f"q2_emitters_{year}.csv")
