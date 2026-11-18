"""AI Footprint page: estimated water/energy/carbon cost of an AI prompt,
explained in everyday terms and tied to real electricity-grid data.

Reference numbers in data/ai_footprint.csv are modeled estimates from
published studies (see data/ai_footprint.py's docstring), not real-time
measurements -- the disclosure banner below says so to the user too.

The page tells one story: how a question becomes pollution -> what YOUR usage
adds up to -> what that equals in everyday life -> why the power grid (not just
the AI) decides the carbon cost -> what can be done about it.
"""

import io

import dash
from dash import Input, Output, dcc, html

import ai_footprint_analysis as aia
import ai_footprint_charts
import analysis
import state
from data.energy import ENERGY_MAX_YEAR

dash.register_page(__name__, path="/ai-footprint", name="AI Footprint", order=0.6)

_MODEL_OPTIONS = sorted(state.loaded.ai_footprint["model"].unique())
_DEFAULT_MODEL = _MODEL_OPTIONS[0]

_USE_CASE_LABELS = {
    "simple_qa": "Simple Q&A",
    "email_summary": "Email / Summary",
    "document_review": "Document Review",
    "coding_agent": "Coding / Agent Session",
}
_USE_CASE_ORDER = (
    state.loaded.ai_footprint[["use_case", "word_count_max"]]
    .drop_duplicates()
    .sort_values("word_count_max")["use_case"]
    .tolist()
)
_USE_CASE_OPTIONS = [{"label": _USE_CASE_LABELS[uc], "value": uc} for uc in _USE_CASE_ORDER]
_DEFAULT_USE_CASE = _USE_CASE_ORDER[0]

_COUNTRY_OPTIONS = sorted(state.loaded.co2_countries["country"].unique())
_LATEST_YEAR = int(state.loaded.co2_countries["year"].max())
_DEFAULT_COUNTRY = analysis.top_emitter(state.loaded.co2_countries, _LATEST_YEAR)

_WEEKS_PER_MONTH = 52 / 12

# Grid data is computed once: aggregates are removed through co2_countries
# (cleaning rule 1) and tiny territories are dropped inside grid_snapshot.
_GRID = aia.grid_snapshot(state.loaded.co2_countries, state.loaded.energy, ENERGY_MAX_YEAR)
_WORLD_ROW = state.loaded.energy[
    (state.loaded.energy["country"] == "World") & (state.loaded.energy["year"] == ENERGY_MAX_YEAR)
]
_WORLD_INTENSITY = (
    float(_WORLD_ROW["carbon_intensity_elec"].iloc[0]) if not _WORLD_ROW.empty else None
)
_GRID_COUNTRIES = set(_GRID["country"])


def _section(title, intro=None):
    """Section heading with an optional plain-language lead-in."""
    parts = [html.Div(title, className="section-title")]
    if intro:
        parts.append(html.P(intro, className="section-intro"))
    return html.Div(parts)


def _step(icon, title, text):
    return html.Div(className="step", children=[
        html.Div(icon, className="step-icon"),
        html.Div(title, className="step-title"),
        html.Div(text, className="step-text"),
    ])


def layout():
    return html.Div([
        html.H2("AI Footprint"),

        # ---- 1. Hero + how a question becomes pollution ----------------
        html.Div(className="hero ai-hero", children=[
            html.H3("Every question you ask an AI has a physical cost"),
            html.P(
                "AI feels weightless, but it runs in huge data centres full of computers. "
                "Those computers need electricity, and that electricity is often made by "
                "burning coal and gas. They also get hot, so they need water to cool down. "
                "This page lets you see — in simple numbers — what your own AI use adds up to."
            ),
        ]),
        html.Div(className="steps", children=[
            _step("💬", "1. You ask", "You type a question or ask for a summary."),
            _step("🖥️", "2. Data centre works", "Thousands of chips do the maths. That uses electricity (Wh)."),
            _step("🏭", "3. Power plant emits", "If the power comes from fossil fuels, CO2 goes into the air."),
            _step("💧", "4. Cooling uses water", "Water cools the machines and is used in making electricity."),
        ]),

        # ---- 2. Controls ----------------------------------------------
        _section(
            "Step 1 · Describe your AI habit",
            "Move the controls and everything below updates. Not sure what to pick? "
            "Leave the defaults and just watch how the numbers change.",
        ),
        html.Div(
            style={
                "display": "flex", "gap": "24px", "flexWrap": "wrap",
                "alignItems": "flex-end",
            },
            children=[
                html.Div(
                    style={"minWidth": "220px"},
                    children=[
                        html.Label("Models to compare:", htmlFor="ai-footprint-models"),
                        dcc.Checklist(
                            id="ai-footprint-models",
                            options=[{"label": m, "value": m} for m in _MODEL_OPTIONS],
                            value=_MODEL_OPTIONS,
                            inline=True,
                        ),
                    ],
                ),
                html.Div(
                    style={"minWidth": "200px"},
                    children=[
                        html.Label("Model you use:", htmlFor="ai-footprint-primary-model"),
                        dcc.Dropdown(
                            id="ai-footprint-primary-model",
                            options=[{"label": m, "value": m} for m in _MODEL_OPTIONS],
                            value=_DEFAULT_MODEL,
                            clearable=False,
                        ),
                    ],
                ),
                html.Div(
                    style={"minWidth": "200px"},
                    children=[
                        html.Label("What do you ask it?", htmlFor="ai-footprint-usecase"),
                        dcc.Dropdown(
                            id="ai-footprint-usecase",
                            options=_USE_CASE_OPTIONS,
                            value=_DEFAULT_USE_CASE,
                            clearable=False,
                        ),
                    ],
                ),
                html.Div(
                    style={"minWidth": "140px"},
                    children=[
                        html.Label("Questions per day:", htmlFor="ai-footprint-queries-per-day"),
                        dcc.Input(
                            id="ai-footprint-queries-per-day", type="number", value=10, min=0, step=1,
                        ),
                    ],
                ),
                html.Div(
                    style={"minWidth": "140px"},
                    children=[
                        html.Label("Days per week:", htmlFor="ai-footprint-days-per-week"),
                        dcc.RadioItems(
                            id="ai-footprint-days-per-week",
                            options=[{"label": "5", "value": 5}, {"label": "7", "value": 7}],
                            value=7, inline=True,
                        ),
                    ],
                ),
                html.Div(
                    style={"minWidth": "200px"},
                    children=[
                        html.Label("Your country:", htmlFor="ai-footprint-country"),
                        dcc.Dropdown(
                            id="ai-footprint-country",
                            options=[{"label": c, "value": c} for c in _COUNTRY_OPTIONS],
                            value=_DEFAULT_COUNTRY,
                            clearable=False,
                        ),
                    ],
                ),
                html.Div(
                    style={"flexBasis": "100%"},
                    children=[
                        html.Label(
                            "Or paste a real prompt (its length picks the use case for you):",
                            htmlFor="ai-footprint-prompt",
                        ),
                        dcc.Textarea(
                            id="ai-footprint-prompt", value="", style={"width": "100%", "height": "60px"},
                        ),
                    ],
                ),
            ],
        ),

        # ---- 3. Monthly totals + everyday equivalents -------------------
        _section(
            "Step 2 · What your month of AI adds up to",
            "Energy is measured in watt-hours (Wh), carbon in grams of CO2-equivalent, "
            "water in millilitres. They are small per question — the point is how they add up.",
        ),
        html.Div(id="ai-footprint-projection-kpis", className="kpi-row"),
        html.Div(id="ai-footprint-equivalents-title", className="section-title", children="…that is the same as"),
        html.Div(id="ai-footprint-equivalents", className="eq-grid"),
        html.Div(id="ai-footprint-scale", className="scale-banner"),

        # ---- 4. Model comparison -----------------------------------------
        _section(
            "Step 3 · Does the choice of AI model matter?",
            "Same request, different models. Lower bars are better. These differences are "
            "this project's rough estimates, so use them to compare, not to quote.",
        ),
        dcc.Graph(id="ai-footprint-model-bar"),

        # ---- 5. Grid -----------------------------------------------------
        _section(
            "Step 4 · The power grid matters as much as the AI",
            "Here is the key idea for sustainability: the SAME AI usage causes very different "
            "pollution depending on how the local electricity is made. A grid full of "
            "hydro, wind and solar is clean; one that burns coal is not. "
            f"(Real data: Our World in Data, grid carbon intensity, {ENERGY_MAX_YEAR}.)",
        ),
        dcc.Graph(id="ai-footprint-grid-bar"),
        html.Div(id="ai-footprint-grid-note", className="insight-box"),

        # ---- 6. Greener-grid what-if -------------------------------------
        _section(
            "Step 5 · What if the grid got greener?",
            "Drag the slider to choose how much of your country's electricity is renewable. "
            "The AI stays exactly the same — only the power behind it changes.",
        ),
        html.Div(style={"maxWidth": "620px", "marginBottom": "10px"}, children=[
            html.Label("Renewable share of electricity (%)", htmlFor="ai-footprint-renewable-slider"),
            dcc.Slider(
                id="ai-footprint-renewable-slider", min=0, max=100, step=5, value=80,
                marks={v: f"{v}%" for v in range(0, 101, 25)},
                tooltip={"placement": "bottom", "always_visible": True},
            ),
        ]),
        dcc.Graph(id="ai-footprint-scenario-bar"),

        # ---- 7. Per capita ----------------------------------------------
        _section(
            "Step 6 · Is it a big deal compared with everything else we emit?",
            "Compare one month of your AI use with the total CO2 each person in your country "
            "causes in a whole year (cars, heating, factories, food…).",
        ),
        dcc.Graph(id="ai-footprint-per-capita"),
        html.Div(id="ai-footprint-per-capita-note", className="insight-box"),

        # ---- 8. What to do -----------------------------------------------
        _section("What can you actually do?", "Three simple choices, with numbers from your own settings."),
        html.Div(id="ai-footprint-tips", className="card-grid"),

        # ---- 9. Honest caveat + glossary --------------------------------
        html.Div(
            className="caveat",
            children=[
                html.Strong("How much can you trust these numbers? "),
                "They are modeled estimates derived from published third-party studies "
                "(MIT News, Jan 2025; Google's 2024 production measurements), not "
                "real-time measurements. Actual per-query cost varies by hardware, "
                "region, and model version. The water figure uses a global "
                "average. The differences between models are this project's own rough "
                "estimate of relative infrastructure scale, not vendor-disclosed data. "
                "The grid section uses each country's average electricity carbon "
                "intensity, so its carbon numbers differ from the baseline in Step 2. "
                "Everyday comparisons (LED bulb 10 W, phone charge 12 Wh, car 250 g CO2/km, "
                "tree 60 g CO2/day, glass 250 mL) are rounded reference values.",
            ],
        ),
        html.Div(style={"marginTop": "18px"}, children=[
            html.Button("Download reference table CSV", id="ai-footprint-download-button"),
            dcc.Download(id="ai-footprint-download-csv"),
        ]),
    ])


def _kpi_card(label, value_text):
    return html.Div(
        className="kpi-card",
        children=[
            html.Div(label, className="kpi-label"),
            html.Div(value_text, className="kpi-value"),
        ],
    )


def _eq_card(icon, value_text, label):
    return html.Div(className="eq-card", children=[
        html.Div(icon, className="eq-icon"),
        html.Div(value_text, className="eq-value"),
        html.Div(label, className="eq-label"),
    ])


def _tip_card(icon, title, text):
    return html.Div(className="nav-card tip-card", children=[
        html.Span(icon, className="tag"),
        html.H3(title),
        html.P(text),
    ])


def _fmt_distance(metres):
    return f"{metres / 1000:,.1f} km" if metres >= 1000 else f"{metres:,.0f} m"


def _fmt_hours(hours):
    return f"{hours * 60:,.0f} min" if hours < 1 else f"{hours:,.1f} h"


def _tips(footprint, model, use_case, country, monthly_energy_wh, grid_rows):
    """Three data-driven suggestions, worded for a general audience."""
    tips = []

    # 1. Pick a lean model.
    same_task = footprint[footprint["use_case"] == use_case].sort_values("energy_wh")
    leanest = same_task.iloc[0]
    mine = same_task[same_task["model"] == model].iloc[0]
    if mine["energy_wh"] > leanest["energy_wh"]:
        saving = (1 - leanest["energy_wh"] / mine["energy_wh"]) * 100
        tips.append(_tip_card(
            "🧠", "Pick a lean model",
            f"For this kind of request, {leanest['model']} is estimated to use {saving:.0f}% "
            f"less energy than {model}. Smaller, efficient models are the easiest win.",
        ))
    else:
        tips.append(_tip_card(
            "🧠", "Good choice already",
            f"{model} is the leanest model in our table for this kind of request. "
            "Keep choosing efficient models as new ones appear.",
        ))

    # 2. Match the tool to the task.
    simple = footprint[(footprint["model"] == model) & (footprint["use_case"] == _USE_CASE_ORDER[0])].iloc[0]
    if mine["energy_wh"] > simple["energy_wh"]:
        tips.append(_tip_card(
            "✂️", "Ask only what you need",
            f"One {_USE_CASE_LABELS[use_case].lower()} request uses about "
            f"{mine['energy_wh'] / simple['energy_wh']:.0f}× the energy of a quick question. "
            "Short, clear prompts — and not re-running the same thing — keep the cost down.",
        ))
    else:
        tips.append(_tip_card(
            "✂️", "Quick questions are cheap",
            "Short questions are the lightest use of AI. The heavier the task "
            "(documents, coding sessions), the more energy it takes.",
        ))

    # 3. Cleaner electricity.
    mine_row = grid_rows[grid_rows["country"] == country]
    if not mine_row.empty:
        cleanest = grid_rows.sort_values("carbon_intensity_elec").iloc[0]
        mine_i = float(mine_row["carbon_intensity_elec"].iloc[0])
        if mine_i > cleanest["carbon_intensity_elec"]:
            cut = (1 - cleanest["carbon_intensity_elec"] / mine_i) * 100
            tips.append(_tip_card(
                "🌱", "Demand cleaner power",
                f"The same AI use on {cleanest['country']}'s grid would emit {cut:.0f}% less CO2 "
                f"than in {country}. Data centres that run on renewables — and a greener national "
                "grid — matter more than any single prompt.",
            ))
            return tips
    tips.append(_tip_card(
        "🌱", "Demand cleaner power",
        "The biggest lever is how electricity is made. Support data centres and "
        "governments that move to wind, solar and hydro.",
    ))
    return tips


@dash.callback(
    Output("ai-footprint-model-bar", "figure"),
    Output("ai-footprint-projection-kpis", "children"),
    Output("ai-footprint-equivalents", "children"),
    Output("ai-footprint-scale", "children"),
    Output("ai-footprint-grid-bar", "figure"),
    Output("ai-footprint-grid-note", "children"),
    Output("ai-footprint-scenario-bar", "figure"),
    Output("ai-footprint-per-capita", "figure"),
    Output("ai-footprint-per-capita-note", "children"),
    Output("ai-footprint-tips", "children"),
    Input("ai-footprint-models", "value"),
    Input("ai-footprint-primary-model", "value"),
    Input("ai-footprint-usecase", "value"),
    Input("ai-footprint-prompt", "value"),
    Input("ai-footprint-queries-per-day", "value"),
    Input("ai-footprint-days-per-week", "value"),
    Input("ai-footprint-country", "value"),
    Input("ai-footprint-renewable-slider", "value"),
)
def update_ai_footprint(
    models, primary_model, use_case_dropdown, prompt_text, queries_per_day, days_per_week, country,
    renewable_target,
):
    footprint = state.loaded.ai_footprint
    selected_models = models or _MODEL_OPTIONS

    bucketed_use_case = aia.bucket_prompt(prompt_text or "", footprint)
    use_case = bucketed_use_case or use_case_dropdown

    bar_fig = ai_footprint_charts.model_comparison_bar(
        footprint, use_case, selected_models, _USE_CASE_LABELS.get(use_case, use_case)
    )

    per_query = footprint[
        (footprint["model"] == primary_model) & (footprint["use_case"] == use_case)
    ].iloc[0]

    monthly_queries = max(0, queries_per_day or 0) * (days_per_week or 7) * _WEEKS_PER_MONTH
    monthly_energy_wh = per_query["energy_wh"] * monthly_queries
    monthly_co2_g = per_query["co2_g"] * monthly_queries
    monthly_water_ml = per_query["water_ml"] * monthly_queries

    kpis = [
        _kpi_card("Questions per month", f"{monthly_queries:,.0f}"),
        _kpi_card("Energy", f"{monthly_energy_wh:,.1f} Wh"),
        _kpi_card("Carbon", f"{monthly_co2_g:,.1f} g CO2e"),
        _kpi_card("Water", f"{monthly_water_ml:,.0f} mL"),
    ]

    # Everyday equivalents.
    eq = aia.equivalents(monthly_energy_wh, monthly_co2_g, monthly_water_ml)
    eq_cards = [
        _eq_card("💡", _fmt_hours(eq["led_hours"]), "of an LED light bulb"),
        _eq_card("📱", f"{eq['phone_charges']:,.1f}", "full phone charges"),
        _eq_card("🚗", _fmt_distance(eq["car_metres"]), "driven in a petrol car"),
        _eq_card("🌳", f"{eq['tree_days']:,.1f} days", "of CO2 a tree absorbs"),
        _eq_card("🥛", f"{eq['water_glasses']:,.1f}", "glasses of water"),
    ]

    # Scaling by 1,000,000 people makes the units line up neatly: Wh -> MWh,
    # g -> tonnes, mL -> thousand litres.
    scale = [
        html.Strong("Now multiply by a million people. "),
        f"If 1,000,000 people used AI like this for a month, that would be about "
        f"{monthly_energy_wh:,.0f} MWh of electricity (a typical home uses ~250 kWh a month, "
        f"so that is around {monthly_energy_wh * 1e6 / 1000 / 250:,.0f} homes), "
        f"{monthly_co2_g:,.1f} tonnes of CO2 and {monthly_water_ml:,.0f} thousand litres of water.",
    ]

    # Grid comparison: same monthly energy on different grids.
    chart_rows = _GRID.sort_values("carbon_intensity_elec")
    picked = list(chart_rows.head(5)["country"]) + list(chart_rows.tail(5)["country"])
    if country in _GRID_COUNTRIES and country not in picked:
        picked.append(country)
    grid_rows = chart_rows[chart_rows["country"].isin(picked)].copy()
    grid_rows["co2_g"] = grid_rows["carbon_intensity_elec"].apply(
        lambda i: aia.grid_co2_g(monthly_energy_wh, i)
    )
    grid_fig = ai_footprint_charts.grid_comparison_bar(
        grid_rows, country,
        None if _WORLD_INTENSITY is None else aia.grid_co2_g(monthly_energy_wh, _WORLD_INTENSITY),
    )

    mine_row = _GRID[_GRID["country"] == country]
    if mine_row.empty:
        grid_note = (
            f"We do not have grid data for {country} (or it has under 1 million people), so it "
            "is not highlighted. The bars still show how much the grid matters."
        )
        scenario_fig = ai_footprint_charts.grid_scenario_bar(country, 0, 0, 0, renewable_target or 0)
        scenario_fig.add_annotation(
            text="No grid data for this country", showarrow=False,
            x=0.5, y=0.5, xref="paper", yref="paper",
        )
    else:
        intensity = float(mine_row["carbon_intensity_elec"].iloc[0])
        renewable_now = float(mine_row["renewables_share_elec"].iloc[0])
        today_g = aia.grid_co2_g(monthly_energy_wh, intensity)
        cleanest = grid_rows.iloc[0]
        dirtiest = grid_rows.iloc[-1]
        ratio = (
            dirtiest["co2_g"] / cleanest["co2_g"]
            if cleanest["co2_g"] > 0 else float("inf")
        )
        ratio_text = "far more" if ratio == float("inf") else f"{ratio:,.0f}× more"
        grid_note = [
            html.Strong(f"{country}: "),
            f"its electricity emits {intensity:,.0f} g of CO2 per kWh and is {renewable_now:.0f}% "
            f"renewable, so your usage causes about {today_g:,.1f} g of CO2 a month. "
            f"On {dirtiest['country']}'s grid the same usage causes {ratio_text} CO2 than on "
            f"{cleanest['country']}'s. Same AI, same prompt — different power.",
        ]
        target = renewable_target if renewable_target is not None else renewable_now
        scenario_g = aia.grid_co2_g(
            monthly_energy_wh, aia.scenario_intensity(intensity, renewable_now, target)
        )
        full_g = aia.grid_co2_g(
            monthly_energy_wh, aia.scenario_intensity(intensity, renewable_now, 100)
        )
        scenario_fig = ai_footprint_charts.grid_scenario_bar(country, today_g, scenario_g, full_g, target)

    # Per-capita context.
    co2_pc_series = analysis.country_series(state.loaded.co2_countries, country, "co2_per_capita")
    latest = analysis.latest_value(co2_pc_series)
    country_co2_pc = latest[1] if latest else None
    share_pct = aia.per_capita_share(monthly_co2_g, country_co2_pc)
    per_capita_fig = ai_footprint_charts.per_capita_comparison(share_pct, country)
    if share_pct is None:
        pc_note = f"No per-person CO2 figure is available for {country}, so no comparison is shown."
    else:
        pc_note = [
            html.Strong("Reading this honestly: "),
            f"one month of your AI use is about {share_pct:.3f}% of the CO2 an average person in "
            f"{country} causes in a year ({country_co2_pc:.1f} tonnes). On its own it is tiny. "
            "The concern is growth: billions of requests a day, new data centres, and fast-rising "
            "electricity demand — which is why cleaner power matters.",
        ]

    tips = _tips(footprint, primary_model, use_case, country, monthly_energy_wh, _GRID)

    return (
        bar_fig, kpis, eq_cards, scale, grid_fig, grid_note, scenario_fig,
        per_capita_fig, pc_note, tips,
    )


@dash.callback(
    Output("ai-footprint-download-csv", "data"),
    Input("ai-footprint-download-button", "n_clicks"),
    prevent_initial_call=True,
)
def download_ai_footprint(n_clicks):
    buffer = io.StringIO()
    state.loaded.ai_footprint.to_csv(buffer, index=False)
    return dict(content=buffer.getvalue(), filename="ai_footprint_reference.csv")
