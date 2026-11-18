"""Overview page: states all four research questions and headline numbers."""

import dash
from dash import dcc, html

import analysis
import state

dash.register_page(__name__, path="/overview", name="Overview", order=0.3)


def layout():
    loaded = state.loaded
    latest_year = int(loaded.co2_countries["year"].max())
    world_latest = loaded.co2_all[
        (loaded.co2_all["country"] == "World") & (loaded.co2_all["year"] == latest_year)
    ].iloc[0]
    latest_temp = loaded.temperature.dropna(subset=["temperature_anomaly"]).iloc[-1]

    top_emitter_name = analysis.top_emitter(loaded.co2_countries, latest_year)
    if top_emitter_name is not None:
        top_emitter_co2 = loaded.co2_countries[
            (loaded.co2_countries["country"] == top_emitter_name)
            & (loaded.co2_countries["year"] == latest_year)
        ]["co2"].iloc[0]
        top_emitter_text = f"{top_emitter_name} ({top_emitter_co2:,.0f} Mt)"
    else:
        top_emitter_text = "No data"

    return html.Div([
        html.Div(className="hero", children=[
            html.Img(src="/assets/img/earth.svg", className="hero-icon", alt=""),
            html.P("Four questions about CO2 emissions, warming, and the energy transition, "
                   "answered with interactive charts built on Our World in Data, NASA GISTEMP and NASA POWER."),
        ]),
        html.Div("Headline numbers", className="section-title"),
        html.Div(className="kpi-row", children=[
            _kpi(f"Global CO2, {latest_year}", f"{world_latest['co2']:,.0f} Mt"),
            _kpi(
                f"Temperature anomaly, {int(latest_temp['year'])}",
                f"{latest_temp['temperature_anomaly']:+.2f}°C",
                "vs 1951-1980",
            ),
            _kpi(f"Top emitter, {latest_year}", top_emitter_text),
        ]),
        html.Div("Research questions", className="section-title"),
        html.Div(className="card-grid", children=[
            _nav_card("/q1", "Growth", "Has global CO2 growth slowed since 2000?",
                      "CO2 and temperature anomaly side by side, with yearly growth rates."),
            _nav_card("/q2", "Emitters", "Who emits most in total, versus per person?",
                      "World map and paired rankings for total and per-capita emissions."),
            _nav_card("/q3", "GDP", "Does higher GDP still mean higher emissions per person?",
                      "GDP against emissions per person, sized by population."),
            _nav_card("/q4", "Renewables", "Is renewable adoption tracking solar/wind potential?",
                      "Which countries beat or lag their natural renewable potential."),
        ]),
        html.Div("Explore further", className="section-title"),
        html.Div(className="card-grid", children=[
            _nav_card("/", "Dashboard", "Climate Dashboard",
                      "One-screen view: globe, warming stripes, rankings and trends for any year.", alt=True),
            _nav_card("/country", "Tool", "Country Profile",
                      "Pick a country and see its headline numbers and trends.", alt=True),
            _nav_card("/compare", "Tool", "Compare Years",
                      "Pick two years and see how the global picture changed.", alt=True),
            _nav_card("/ai-footprint", "Tool", "AI Footprint",
                      "Estimate the energy, carbon and water cost of an AI prompt.", alt=True),
        ]),
    ])


def _kpi(label, value, note=None):
    """Headline-number card."""
    children = [html.Div(label, className="kpi-label"), html.Div(value, className="kpi-value")]
    if note:
        children.append(html.Div(note, className="kpi-label"))
    return html.Div(className="kpi-card", children=children)


_ICONS = {"/": "sun", "/q1": "factory", "/q2": "earth", "/q3": "leaf", "/q4": "turbine",
          "/country": "tree", "/compare": "solar", "/ai-footprint": "drop"}


def _nav_card(href, tag, title, blurb, alt=False):
    """Clickable card linking to one of the dashboard pages."""
    return dcc.Link(
        href=href,
        className="nav-card",
        children=[
            html.Img(src=f"/assets/img/{_ICONS[href]}.svg", className="card-icon", alt=""),
            html.Span(tag, className="tag alt" if alt else "tag"),
            html.H3(title),
            html.P(blurb),
        ],
    )
