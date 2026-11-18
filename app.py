"""Dash application shell for the Global Climate Trends dashboard.

Page layouts and callbacks live under pages/ (one module per question);
this file only builds the app object, top navigation, and footer. Data is
loaded once, in state.py, imported below before Dash scans pages/.
"""

import dash
import plotly.graph_objects as go
import plotly.io as pio
from dash import ALL, Input, Output, State, dcc, html

import state  # noqa: F401 -- importing triggers data.load_all() once

app = dash.Dash(__name__, use_pages=True)
app.title = "Global Climate Trends"
server = app.server  # gunicorn entry point: app:server

# Shared Plotly look so every chart matches the page styling in assets/style.css.
_CLIMATE_TEMPLATE = go.layout.Template(pio.templates["plotly_white"])
_CLIMATE_TEMPLATE.layout.update(
    font={"family": "Inter, Segoe UI, system-ui, Arial, sans-serif", "color": "#17313a"},
    colorway=["#2f7d4f", "#d98a3d", "#1f4e5f", "#e9c46a", "#6cc487", "#8c6a4a"],
    paper_bgcolor="rgba(0,0,0,0)",
    hoverlabel={"font_size": 13},
)
pio.templates["climate"] = _CLIMATE_TEMPLATE
pio.templates.default = "climate"

app.layout = html.Div(
    children=[
        dcc.Location(id="url"),
        html.Header(className="site-header", children=html.Div(className="site-header-inner", children=[
            html.Img(src="/assets/img/hero.svg", className="header-art", alt=""),
            html.Div([html.Img(src="/assets/img/leaf.svg", className="brand-leaf", alt=""),
                      html.H1("Global Climate Trends", className="site-title")], className="brand"),
            html.P("Emissions, warming and the energy transition, explored interactively.", className="site-tagline"),
            html.Nav(id="site-nav", className="site-nav", children=[
                html.A(page["name"], href=page["relative_path"], id={"type": "nav-link", "path": page["relative_path"]})
                for page in dash.page_registry.values()
            ]),
        ])),
        html.Main(className="page-wrap", children=dash.page_container),
        html.Footer(
            className="site-footer",
            children=[
                html.P([
                    "CO2, GDP, and energy data: Our World in Data, ",
                    html.A("co2-data", href="https://github.com/owid/co2-data", target="_blank"),
                    " and ",
                    html.A("energy-data", href="https://github.com/owid/energy-data", target="_blank"),
                    " (CC BY 4.0). ",
                ]),
                html.P([
                    "Temperature data: NASA GISS, ",
                    html.A("GISTEMP v4", href="https://data.giss.nasa.gov/gistemp/", target="_blank"),
                    " (public domain). Solar/wind climatology: NASA ",
                    html.A("POWER", href="https://power.larc.nasa.gov/", target="_blank"),
                    " (public domain).",
                ]),
                html.P([
                    "AI footprint estimates: modeled from MIT News, ",
                    html.A(
                        "\"Explained: Generative AI's environmental impact\"",
                        href="https://news.mit.edu/2025/explained-generative-ai-environmental-impact-0117",
                        target="_blank",
                    ),
                    " (Jan 2025), cross-checked for plausibility against the ",
                    html.A(
                        "ClimateAligned AI Footprint Calculator",
                        href="https://www.climatealigned.co/tools/ai-footprint-calculator",
                        target="_blank",
                    ),
                    " methodology. Not measured data — see the AI Footprint page for the full caveat.",
                ]),
            ],
        ),
    ],
)


@app.callback(
    Output({"type": "nav-link", "path": ALL}, "className"),
    Input("url", "pathname"),
    State({"type": "nav-link", "path": ALL}, "id"),
)
def highlight_active_nav(pathname, link_ids):
    """Mark the nav link for the current page as active."""
    return ["active" if link["path"] == pathname else "" for link in link_ids]


if __name__ == "__main__":
    app.run(debug=True)
