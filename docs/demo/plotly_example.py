"""The SAME two charts as matplotlib_example.py, built with Plotly instead.

This is the "why Plotly" demo in code form. Compare this file to
matplotlib_example.py line by line: both read the same tiny dataset from
demo_data.py, both produce the same two chart types (a line chart and a
sized bubble scatter) — but here, hover tooltips, zoom, pan, and legend
toggling all come for free, with zero extra code. Nothing below manually
places a text label or manually scales a bubble size; px.scatter's `size=`
and `hover_name=` arguments do it.

This is a deliberately small stand-in for the real thing: the actual Q1 and
Q3 charts in prototype_charts.py use this exact same Plotly API
(px.line-equivalent via go.Scatter, and px.scatter with size + log_x) on
the full ~50,000-row OWID dataset instead of these 8-10 rows.

Output: docs/demo/output/plotly_*.html — open these in a browser and:
  - hover over any point/line to see the exact value in a tooltip
  - click-drag a rectangle to zoom into a region, double-click to reset
  - click a legend entry to hide/show that series
  - use the camera icon in the top-right toolbar to download a PNG
None of that interactivity required writing a single extra line of code.
"""

from pathlib import Path

import plotly.express as px

from demo_data import GDP_CO2_SNAPSHOT, WORLD_CO2_TREND

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def line_chart():
    fig = px.line(
        WORLD_CO2_TREND, x="year", y="co2_mt", markers=True,
        title="World CO2 emissions, 2015-2024 (Plotly, interactive)",
        labels={"year": "Year", "co2_mt": "CO2 (Mt)"},
    )
    fig.write_html(OUTPUT_DIR / "plotly_line.html")


def bubble_chart():
    fig = px.scatter(
        GDP_CO2_SNAPSHOT,
        x="gdp_per_capita", y="co2_per_capita",
        size="population_millions",   # bubble size, computed automatically
        color="continent",            # legend + color, one keyword
        hover_name="country",         # this is the whole "hover" feature
        log_x=True,                   # log axis, one keyword, same as Matplotlib's set_xscale
        title="GDP per capita vs CO2 per capita (Plotly, interactive)",
        labels={"gdp_per_capita": "GDP per capita, log scale (USD)", "co2_per_capita": "CO2 per capita (t)"},
    )
    fig.write_html(OUTPUT_DIR / "plotly_bubble.html")


if __name__ == "__main__":
    line_chart()
    bubble_chart()
    print("Saved: output/plotly_line.html, output/plotly_bubble.html")
    print("Open them in a browser and try: hover, drag-to-zoom, double-click")
    print("to reset, click a legend entry to hide a continent's countries.")
