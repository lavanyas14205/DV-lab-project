"""AI Footprint page charts: per-model comparison, grid comparison,
greener-grid scenario and per-capita context."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

# One colour per resource so the same idea always looks the same on the page:
# amber = energy, slate = carbon, blue = water.
_METRICS = [
    ("energy_wh", "Energy (Wh)", "#e9a23b"),
    ("co2_g", "Carbon (g CO2e)", "#475569"),
    ("water_ml", "Water (mL)", "#2b8cbe"),
]
_TEAL = "#0f766e"
_CORAL = "#e76f51"
_GREY = "#b8c4c2"


def model_comparison_bar(footprint, use_case, models, use_case_label):
    """One subplot per metric (each has its own unit, so they don't share
    a y-axis), one bar per model, for the selected use case."""
    subset = footprint[(footprint["use_case"] == use_case) & (footprint["model"].isin(models))]
    fig = make_subplots(rows=1, cols=3, subplot_titles=[label for _, label, _ in _METRICS])
    for i, (column, _label, colour) in enumerate(_METRICS, start=1):
        fig.add_trace(
            go.Bar(
                x=subset["model"], y=subset[column], marker_color=colour,
                text=subset[column].round(2), textposition="outside", showlegend=False,
            ),
            row=1, col=i,
        )
        fig.update_yaxes(rangemode="tozero", row=1, col=i)
    fig.update_layout(title=f"One request, model by model — {use_case_label}", margin={"t": 90})
    return fig


def grid_comparison_bar(rows, selected_country, world_g):
    """Horizontal bars: grams of CO2 for the SAME monthly AI usage on
    different countries' electricity grids. `rows` has columns country and
    co2_g, sorted ascending. The user's chosen country is highlighted; a
    dashed line marks the world-average grid."""
    colours = [_CORAL if c == selected_country else _TEAL for c in rows["country"]]
    fig = go.Figure(go.Bar(
        x=rows["co2_g"], y=rows["country"], orientation="h", marker_color=colours,
        text=[f"{v:,.1f} g" for v in rows["co2_g"]], textposition="outside",
    ))
    if world_g is not None:
        fig.add_vline(
            x=world_g, line_dash="dash", line_color="#17313a",
            annotation_text="World average grid", annotation_position="top",
        )
    fig.update_layout(
        title="Same AI usage, different power grids — monthly CO2 (g)",
        xaxis_title="grams of CO2e per month", yaxis={"autorange": "reversed"},
        margin={"r": 70}, height=480,
    )
    return fig


def grid_scenario_bar(country, today_g, scenario_g, full_g, scenario_pct):
    """Three bars: today's real grid, the user's what-if renewable share,
    and a 100%-renewable grid. Shows how much of AI's footprint is really
    a question about electricity, not about the AI itself."""
    labels = ["Today", f"If {scenario_pct:.0f}% renewable", "If 100% renewable"]
    fig = go.Figure(go.Bar(
        x=labels, y=[today_g, scenario_g, full_g],
        marker_color=[_GREY, _TEAL, "#2a9d8f"],
        text=[f"{v:,.1f} g" for v in (today_g, scenario_g, full_g)], textposition="outside",
    ))
    fig.update_layout(
        title=f"Monthly AI carbon in {country}: what a cleaner grid would change",
        yaxis_title="grams of CO2e per month", yaxis={"rangemode": "tozero"}, showlegend=False,
    )
    return fig


def per_capita_comparison(share_pct, country):
    """Single bar: projected AI usage as % of one person's annual
    per-capita CO2 in `country`. share_pct is None when the country has no
    per-capita CO2 data for its latest year -- shown as an annotation, not
    a fake 0%.
    """
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[country], y=[share_pct], marker_color=_CORAL, name="AI usage",
        text=[None if share_pct is None else f"{share_pct:.3f}%"], textposition="outside",
    ))
    fig.update_layout(
        title=f"One month of AI use vs a year of {country}'s per-person CO2",
        yaxis_title="% of one person's annual CO2 footprint",
        yaxis={"rangemode": "tozero"},
    )
    if share_pct is None:
        fig.add_annotation(
            text="No per-capita CO2 data for this country's latest year",
            showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper",
        )
    return fig
