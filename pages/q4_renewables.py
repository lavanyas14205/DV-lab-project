"""Q4 page: is renewable adoption tracking natural solar/wind potential?"""

import io

import dash
from dash import Input, Output, dcc, html

import data
import q4_charts
import state
from data.energy import ENERGY_MAX_YEAR, RENEWABLE_SHARE_COLUMN

dash.register_page(__name__, path="/q4", name="Renewables", order=4)

_MIN_YEAR = data.DEFAULT_YEAR_RANGE[0]
_MAX_YEAR = ENERGY_MAX_YEAR


def layout():
    return html.Div([
        html.H2("Is renewable adoption tracking natural solar/wind potential?"),
        html.Div(
            style={"display": "flex", "gap": "30px", "flexWrap": "wrap", "alignItems": "flex-end"},
            children=[
                html.Div(
                    style={"flex": "2", "minWidth": "300px"},
                    children=[
                        html.Label("Year:", htmlFor="q4-year-slider"),
                        dcc.Slider(
                            id="q4-year-slider", min=_MIN_YEAR, max=_MAX_YEAR, step=1, value=_MAX_YEAR,
                            marks={y: str(y) for y in range(_MIN_YEAR, _MAX_YEAR + 1, 5)},
                            tooltip={"placement": "bottom", "always_visible": True},
                        ),
                    ],
                ),
                html.Div(
                    style={"flex": "1", "minWidth": "180px"},
                    children=[
                        html.Label("Potential:", htmlFor="q4-potential-toggle"),
                        dcc.RadioItems(
                            id="q4-potential-toggle",
                            options=[
                                {"label": "Solar", "value": "solar"},
                                {"label": "Wind", "value": "wind"},
                            ],
                            value="solar", inline=True,
                        ),
                    ],
                ),
                html.Div([
                    html.Button("Download filtered CSV", id="q4-download-button"),
                    dcc.Download(id="q4-download-csv"),
                ]),
            ],
        ),
        dcc.Graph(id="q4-bubble"),
        html.Div(
            id="q4-outliers",
            style={"display": "flex", "gap": "40px", "flexWrap": "wrap", "marginTop": "20px"},
        ),
        html.P(
            "Solar/wind potential here is a single NASA POWER climatology sample taken at "
            "each country's capital city — a proxy for national resource availability, not "
            "a direct national measurement.",
            style={"fontSize": "0.85em", "color": "#555", "marginTop": "10px"},
        ),
    ])


def _energy_for_year(year):
    energy_countries = data.filter_countries(state.loaded.energy)
    return energy_countries[energy_countries["year"] == year]


def _outlier_item(row, potential_col, unit):
    return html.Li(
        f"{row['country']} — {row[RENEWABLE_SHARE_COLUMN]:.0f}% renewable electricity "
        f"(potential {row[potential_col]:.1f} {unit})"
    )


@dash.callback(
    Output("q4-bubble", "figure"),
    Output("q4-outliers", "children"),
    Input("q4-year-slider", "value"),
    Input("q4-potential-toggle", "value"),
)
def update_q4(year, potential):
    energy_year = _energy_for_year(year)
    fig = q4_charts.renewable_potential_vs_adoption_bubble(
        energy_year, state.loaded.climatology, potential=potential
    )

    outliers = q4_charts.outlier_details(energy_year, state.loaded.climatology, potential=potential)
    potential_col = q4_charts.POTENTIAL_COLUMNS[potential]
    unit = q4_charts.POTENTIAL_UNITS[potential]

    outlier_children = [
        html.Div(
            style={"flex": "1", "minWidth": "280px"},
            children=[
                html.H4("🚀 Adoption Leaders"),
                html.P(
                    "Above the fitted trend: renewable adoption is relatively high "
                    "compared with measured solar/wind potential."
                ),
                html.Ul([_outlier_item(row, potential_col, unit) for row in outliers["leaders"]]),
            ],
        ),
        html.Div(
            style={"flex": "1", "minWidth": "280px"},
            children=[
                html.H4("⚠️ Potential Under-Utilisers"),
                html.P(
                    "Below the fitted trend: renewable adoption is relatively low "
                    "compared with measured solar/wind potential."
                ),
                html.Ul([_outlier_item(row, potential_col, unit) for row in outliers["under_utilisers"]]),
            ],
        ),
    ]
    return fig, outlier_children


@dash.callback(
    Output("q4-download-csv", "data"),
    Input("q4-download-button", "n_clicks"),
    Input("q4-year-slider", "value"),
    Input("q4-potential-toggle", "value"),
    prevent_initial_call=True,
)
def download_q4(n_clicks, year, potential):
    if dash.callback_context.triggered_id != "q4-download-button":
        raise dash.exceptions.PreventUpdate
    energy_year = _energy_for_year(year)
    merged = energy_year.merge(state.loaded.climatology, on="iso_code", how="inner")
    buffer = io.StringIO()
    merged.to_csv(buffer, index=False)
    return dict(content=buffer.getvalue(), filename=f"q4_renewables_{year}.csv")
