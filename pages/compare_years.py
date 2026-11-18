"""Compare Years page: global metrics at two chosen years, side by side."""

import dash
from dash import Input, Output, dcc, html

import analysis
import data
import state
from data.energy import ENERGY_MAX_YEAR, RENEWABLE_SHARE_COLUMN

dash.register_page(__name__, path="/compare", name="Compare Years", order=6)

_MIN_YEAR = data.DEFAULT_YEAR_RANGE[0]
_MAX_YEAR = int(state.loaded.co2_countries["year"].max())

# "World" aggregate rows carry the global totals used here — the same rows
# prototype_charts.emissions_temperature_line uses for the Q1 line chart.
_WORLD_CO2 = state.loaded.co2_all[state.loaded.co2_all["country"] == "World"]
_WORLD_ENERGY = state.loaded.energy[state.loaded.energy["country"] == "World"]
_TEMPERATURE = state.loaded.temperature

# (label, frame, column, change type, max year). "absolute" is used for
# temperature anomaly, where a percent change is meaningless near a
# near-zero baseline. max year is the cap for columns whose coverage drops
# off past a certain year (renewables_share_elec — rule 7); None means no cap.
_ROWS = [
    ("Global CO2 emissions (Mt)", _WORLD_CO2, "co2", "percent", None),
    ("CO2 per person (t)", _WORLD_CO2, "co2_per_capita", "percent", None),
    (
        f"Renewable electricity share (%, capped at {ENERGY_MAX_YEAR})",
        _WORLD_ENERGY,
        RENEWABLE_SHARE_COLUMN,
        "percent",
        ENERGY_MAX_YEAR,
    ),
    ("Temperature anomaly (°C)", _TEMPERATURE, "temperature_anomaly", "absolute", None),
]


def layout():
    years = list(range(_MIN_YEAR, _MAX_YEAR + 1))
    year_options = [{"label": str(y), "value": y} for y in years]
    return html.Div([
        html.H2("Compare Years"),
        html.P("Pick two years to see how the global picture changed between them."),
        html.Div(
            style={"display": "flex", "gap": "20px", "alignItems": "flex-end"},
            children=[
                html.Div([
                    html.Label("From year:", htmlFor="compare-year-from"),
                    dcc.Dropdown(
                        id="compare-year-from", options=year_options, value=_MIN_YEAR, clearable=False
                    ),
                ]),
                html.Div([
                    html.Label("To year:", htmlFor="compare-year-to"),
                    dcc.Dropdown(
                        id="compare-year-to", options=year_options, value=_MAX_YEAR, clearable=False
                    ),
                ]),
            ],
        ),
        html.Div(id="compare-years-table", style={"marginTop": "20px"}),
    ])


def _format_value(value):
    return f"{value:,.2f}" if value is not None else "n/a"


@dash.callback(
    Output("compare-years-table", "children"),
    Input("compare-year-from", "value"),
    Input("compare-year-to", "value"),
)
def update_compare_years(year_from, year_to):
    rows = []
    for label, frame, column, change_type, max_year in _ROWS:
        row_year_from = min(year_from, max_year) if max_year is not None else year_from
        row_year_to = min(year_to, max_year) if max_year is not None else year_to
        from_value = analysis.value_at_year(frame, row_year_from, column)
        to_value = analysis.value_at_year(frame, row_year_to, column)
        if change_type == "percent":
            change = analysis.percent_change(from_value, to_value)
            change_text = f"{change:+.1f}%" if change is not None else "n/a"
        else:
            change = analysis.absolute_change(from_value, to_value)
            change_text = f"{change:+.2f}" if change is not None else "n/a"
        rows.append(
            html.Tr([
                html.Td(label),
                html.Td(_format_value(from_value)),
                html.Td(_format_value(to_value)),
                html.Td(change_text),
            ])
        )
    return html.Table(
        [html.Thead(html.Tr([html.Th("Metric"), html.Th(str(year_from)), html.Th(str(year_to)), html.Th("Change")]))]
        + [html.Tbody(rows)],
        style={"borderCollapse": "collapse", "width": "100%"},
    )
