"""Dashboard page (/dashboard): one-screen "mission control" view of the whole story.

A single year slider and a metric toggle drive every panel: four headline tiles,
a "warming stripes" ribbon of observed temperature, a draggable globe, the top-10
emitters, and the CO2-vs-temperature trend. Everything is read from state.loaded
(cleaned once at startup), so the aggregate filter, per-capita population floor
and energy-year cap from CLAUDE.md are applied the same way as on the other pages.
"""

import dash
import numpy as np
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

import data
import state
from data.energy import ENERGY_MAX_YEAR

dash.register_page(__name__, path="/", name="Dashboard", order=0)

_MIN_YEAR = data.DEFAULT_YEAR_RANGE[0]
_MAX_YEAR = int(state.loaded.co2_countries["year"].max())

# Dark "night mode" palette used only on this page (see .dash-board in style.css).
_INK, _MUTED, _GRID = "#e8f1f2", "#8fa7ad", "rgba(255,255,255,0.08)"
_TEAL, _CORAL, _GOLD = "#7bd88f", "#ef8354", "#f2c14e"


def _dark(fig, height):
    """Shared transparent dark styling so every panel matches the dashboard."""
    fig.update_layout(
        height=height, margin={"l": 10, "r": 10, "t": 10, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": _INK, "family": "Inter, Segoe UI, system-ui, sans-serif", "size": 12},
        hoverlabel={"bgcolor": "#0b2417", "font_color": _INK},
    )
    return fig


def layout():
    return html.Div(className="dash-board", children=[
        html.Div(className="db-top", children=[
            html.Div([
                html.Img(src="/assets/img/tree.svg", className="db-badge", alt=""),
                html.Div("SUSTAINABILITY DASHBOARD", className="db-eyebrow"),
                html.H2("The planet at a glance", className="db-title"),
            ]),
            html.Div(className="db-controls", children=[
                html.Div([
                    html.Label("Year", htmlFor="db-year"),
                    dcc.Slider(
                        id="db-year", min=_MIN_YEAR, max=_MAX_YEAR, step=1, value=_MAX_YEAR,
                        marks={y: str(y) for y in range(_MIN_YEAR, _MAX_YEAR + 1, 5)},
                    ),
                ], className="db-year-box"),
                html.Div([
                    html.Label("Map & ranking", htmlFor="db-metric"),
                    dcc.RadioItems(
                        id="db-metric", value="co2",
                        options=[{"label": "Total CO₂", "value": "co2"},
                                 {"label": "CO₂ per person", "value": "co2_per_capita"}],
                        inline=True, className="db-radio",
                    ),
                ]),
            ]),
        ]),
        html.Div(id="db-tiles", className="db-tiles"),
        html.Div(className="db-panel", children=[
            html.Div("Warming stripes · observed global temperature, 1880 to now", className="db-panel-title"),
            dcc.Graph(id="db-stripes", config={"displayModeBar": False}),
            html.Div("Each bar is one year (GISTEMP anomaly vs 1951-1980). Blue is cooler, red is warmer; "
                     "the white marker is the selected year.", className="db-note"),
        ]),
        html.Div(className="db-grid", children=[
            html.Div(className="db-panel", children=[
                html.Div(id="db-globe-title", className="db-panel-title"),
                dcc.Graph(id="db-globe", config={"displayModeBar": False}),
                html.Div("Drag the globe to rotate it.", className="db-note"),
            ]),
            html.Div(className="db-panel", children=[
                html.Div(id="db-rank-title", className="db-panel-title"),
                dcc.Graph(id="db-rank", config={"displayModeBar": False}),
            ]),
        ]),
        html.Div(className="db-panel", children=[
            html.Div("Global CO₂ and temperature anomaly over time", className="db-panel-title"),
            dcc.Graph(id="db-trend", config={"displayModeBar": False}),
        ]),
        html.Div(className="db-eco", children=[
            html.Div([html.Img(src=f"/assets/img/{i}.svg", alt=""), html.Span(t)])
            for i, t in (("turbine", "Wind"), ("solar", "Solar"), ("tree", "Forests"), ("drop", "Water"), ("leaf", "Net zero"))
        ]),
        html.Div(className="db-links", children=[
            dcc.Link("Dig deeper: Growth →", href="/q1"),
            dcc.Link("Who emits →", href="/q2"),
            dcc.Link("GDP →", href="/q3"),
            dcc.Link("Renewables →", href="/q4"),
        ]),
    ])


def _tile(label, value, note, accent, icon):
    return html.Div(className="db-tile", style={"--tile": accent}, children=[
        html.Img(src=f"/assets/img/{icon}.svg", className="db-tile-icon", alt=""),
        html.Div(label, className="db-tile-label"),
        html.Div(value, className="db-tile-value"),
        html.Div(note, className="db-tile-note"),
    ])


@dash.callback(Output("db-tiles", "children"), Input("db-year", "value"))
def update_tiles(year):
    co2_all, temp, energy = state.loaded.co2_all, state.loaded.temperature, state.loaded.energy
    world = co2_all[co2_all["country"] == "World"].set_index("year")

    now = world.loc[year, "co2"]
    prev = world.loc[year - 1, "co2"] if (year - 1) in world.index else None
    growth = f"{(now / prev - 1) * 100:+.1f}% vs {year - 1}" if prev else "first year in view"

    t = temp.dropna(subset=["temperature_anomaly"]).set_index("year")["temperature_anomaly"]
    t_year = year if year in t.index else int(t.index.max())
    t_note = f"{t[t_year] - t[t_year - 1]:+.2f}°C vs {t_year - 1}" if (t_year - 1) in t.index else "vs 1951-1980"

    ctry = state.loaded.co2_countries
    cy = ctry[(ctry["year"] == year)].dropna(subset=["co2"])
    top = cy.loc[cy["co2"].idxmax()]
    share = top["co2"] / now * 100

    ren_year = min(year, ENERGY_MAX_YEAR)  # energy coverage thins after 2023 (CLAUDE.md rule 7)
    ew = energy[(energy["country"] == "World") & (energy["year"] == ren_year)]["renewables_share_elec"]
    ren = f"{ew.iloc[0]:.1f}%" if len(ew) and ew.notna().all() else "n/a"
    ren_note = "of world electricity" + ("" if ren_year == year else f" (latest: {ren_year})")

    return [
        _tile(f"Global CO₂ · {year}", f"{now / 1000:,.1f} Gt", growth, _CORAL, "factory"),
        _tile(f"Temperature anomaly · {t_year}", f"{t[t_year]:+.2f}°C", t_note, _GOLD, "sun"),
        _tile(f"Top emitter · {year}", str(top["country"]), f"{top['co2']:,.0f} Mt · {share:.0f}% of world", _TEAL, "earth"),
        _tile("Renewable electricity", ren, ren_note, "#8fd3e8", "turbine"),
    ]


@dash.callback(Output("db-stripes", "figure"), Input("db-year", "value"))
def update_stripes(year):
    temp = state.loaded.temperature.dropna(subset=["temperature_anomaly"])
    lim = max(abs(temp["temperature_anomaly"]).max(), 0.5)
    fig = go.Figure(go.Heatmap(
        x=temp["year"], z=[temp["temperature_anomaly"]], zmin=-lim, zmax=lim,
        colorscale="RdBu_r", showscale=False, xgap=0,
        hovertemplate="%{x}: %{z:+.2f}°C<extra></extra>",
    ))
    if year in set(temp["year"]):
        fig.add_vline(x=year, line={"color": "#ffffff", "width": 3})
    fig.update_yaxes(visible=False)
    fig.update_xaxes(showgrid=False, color=_MUTED)
    return _dark(fig, 130)


def _metric_frame(year, metric):
    """Country rows for one year; per-person views drop countries under 1M people (rule 6)."""
    df = state.loaded.co2_countries
    df = df[df["year"] == year].dropna(subset=[metric])
    if metric == "co2_per_capita":
        df = data.filter_min_population(df)
    return df


@dash.callback(
    Output("db-globe", "figure"), Output("db-globe-title", "children"),
    Output("db-rank", "figure"), Output("db-rank-title", "children"),
    Input("db-year", "value"), Input("db-metric", "value"),
)
def update_map_and_rank(year, metric):
    df = _metric_frame(year, metric)
    label = "Total CO₂ (Mt)" if metric == "co2" else "CO₂ per person (t)"
    # Log colour scale so a few giant emitters do not wash out everyone else.
    z = np.log10(df[metric].clip(lower=0.01))
    ticks = [0.1, 1, 10, 100, 1000, 10000] if metric == "co2" else [0.1, 1, 3, 10, 30]
    ticks = [t for t in ticks if np.log10(t) <= z.max() + 0.2 and np.log10(t) >= z.min() - 0.2]
    globe = go.Figure(go.Choropleth(
        locations=df["iso_code"], z=z, text=df["country"], customdata=df[metric],
        colorscale=[[0, "#17402b"], [0.35, "#4cae6b"], [0.7, "#f2c14e"], [1, "#e8603a"]],
        marker_line_color="rgba(255,255,255,0.25)", marker_line_width=0.4,
        hovertemplate="<b>%{text}</b><br>" + label + ": %{customdata:,.1f}<extra></extra>",
        colorbar={"title": {"text": label, "font": {"size": 11}}, "tickvals": [np.log10(t) for t in ticks],
                  "ticktext": [f"{t:g}" for t in ticks], "len": 0.7, "thickness": 10, "tickfont": {"color": _MUTED}},
    ))
    globe.update_geos(
        projection_type="orthographic", showland=True, landcolor="#10281b", showocean=True,
        oceancolor="#07140d", showcountries=False, showcoastlines=False, bgcolor="rgba(0,0,0,0)",
        projection_rotation={"lon": 20, "lat": 15},
    )
    _dark(globe, 430)

    top = df.nlargest(10, metric).sort_values(metric)
    bar = go.Figure(go.Bar(
        x=top[metric], y=top["country"], orientation="h",
        marker={"color": top[metric], "colorscale": [[0, "#4cae6b"], [1, "#ef8354"]]},
        text=[f"{v:,.1f}" for v in top[metric]], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x:,.1f}<extra></extra>",
    ))
    bar.update_xaxes(showgrid=True, gridcolor=_GRID, color=_MUTED, title=label)
    bar.update_yaxes(color=_INK, automargin=True, ticksuffix="  ")
    _dark(bar, 430)
    bar.update_layout(margin={"l": 10, "r": 50, "t": 10, "b": 10})

    note = "" if metric == "co2" else " · countries under 1M people excluded"
    return globe, f"{label} by country · {year}", bar, f"Top 10 · {label} · {year}{note}"


@dash.callback(Output("db-trend", "figure"), Input("db-year", "value"))
def update_trend(year):
    co2_all, temp = state.loaded.co2_all, state.loaded.temperature
    world = co2_all[(co2_all["country"] == "World") & (co2_all["year"] >= _MIN_YEAR)]
    temp = temp.dropna(subset=["temperature_anomaly"])
    temp = temp[temp["year"] >= _MIN_YEAR]

    fig = go.Figure()
    fig.add_scatter(x=world["year"], y=world["co2"] / 1000, name="Global CO₂ (Gt)", mode="lines",
                    line={"color": _CORAL, "width": 3}, fill="tozeroy", fillcolor="rgba(239,131,84,0.12)",
                    hovertemplate="%{x}: %{y:.1f} Gt<extra></extra>")
    fig.add_scatter(x=temp["year"], y=temp["temperature_anomaly"], name="Temperature anomaly (°C)",
                    mode="lines", yaxis="y2", line={"color": _GOLD, "width": 3},
                    hovertemplate="%{x}: %{y:+.2f}°C<extra></extra>")
    fig.add_vline(x=year, line={"color": "#ffffff", "width": 1, "dash": "dot"})
    fig.update_layout(
        yaxis={"title": "CO₂ (Gt)", "gridcolor": _GRID, "color": _CORAL},
        yaxis2={"title": "Anomaly (°C)", "overlaying": "y", "side": "right", "showgrid": False, "color": _GOLD},
        xaxis={"gridcolor": _GRID, "color": _MUTED},
        legend={"orientation": "h", "y": 1.12, "x": 0},
    )
    return _dark(fig, 360)
