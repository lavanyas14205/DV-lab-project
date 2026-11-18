"""The SAME two charts as plotly_example.py, built with Matplotlib instead.

Run this, then open plotly_example.py's output next to it — same data,
same two chart types, so the only thing that differs is the library. That
difference is the whole "why Plotly" argument, made concrete instead of
just asserted.

Output, two formats:
  - docs/demo/output/matplotlib_*.png  the raw static image
  - docs/demo/output/matplotlib_*.html a browser-openable wrapper around the
    SAME png (image embedded inline, no separate file to keep track of) —
    built only so both libraries hand you a .html file to open side by side.
    Opening it in a browser does not make it interactive: it is still just
    a picture of a chart, sitting inside a web page. That's the point —
    compare it to plotly_line.html / plotly_bubble.html, which are also
    .html files but respond to hover, drag-zoom, and legend clicks.
"""

import base64
from pathlib import Path

import matplotlib.pyplot as plt

from demo_data import GDP_CO2_SNAPSHOT, WORLD_CO2_TREND

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def _wrap_as_html(png_path: Path, title: str) -> Path:
    """Embed a PNG in a minimal HTML page, for format parity with the Plotly
    .html outputs — NOT for interactivity, which a plain <img> cannot have."""
    encoded = base64.b64encode(png_path.read_bytes()).decode("ascii")
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{title}</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 20px;">
  <h2>{title}</h2>
  <p style="color: #666;">Matplotlib output, opened as HTML for comparison —
  this is still a static &lt;img&gt;: no hover, no zoom, no legend clicks.
  Compare with the Plotly .html file for the same chart.</p>
  <img src="data:image/png;base64,{encoded}" style="max-width: 90%;">
</body></html>
"""
    html_path = png_path.with_suffix(".html")
    html_path.write_text(html, encoding="utf-8")
    return html_path


def line_chart():
    fig, ax = plt.subplots()
    ax.plot(WORLD_CO2_TREND["year"], WORLD_CO2_TREND["co2_mt"], marker="o")
    ax.set_title("World CO2 emissions, 2015-2024 (Matplotlib, static)")
    ax.set_xlabel("Year")
    ax.set_ylabel("CO2 (Mt)")
    png_path = OUTPUT_DIR / "matplotlib_line.png"
    fig.savefig(png_path, dpi=120)
    plt.close(fig)
    _wrap_as_html(png_path, "World CO2 emissions, 2015-2024 (Matplotlib, static)")


def bubble_chart():
    fig, ax = plt.subplots(figsize=(7, 5))
    df = GDP_CO2_SNAPSHOT
    ax.scatter(
        df["gdp_per_capita"], df["co2_per_capita"],
        s=df["population_millions"] * 2,  # manual size scaling — Plotly does this for you
        alpha=0.6,
    )
    # Matplotlib has no built-in hover tooltip, so every label that Plotly
    # gives you for free has to be manually placed as static text instead:
    for _, row in df.iterrows():
        ax.annotate(row["country"], (row["gdp_per_capita"], row["co2_per_capita"]))
    ax.set_xscale("log")
    ax.set_title("GDP per capita vs CO2 per capita (Matplotlib, static)")
    ax.set_xlabel("GDP per capita, log scale (USD)")
    ax.set_ylabel("CO2 per capita (t)")
    png_path = OUTPUT_DIR / "matplotlib_bubble.png"
    fig.savefig(png_path, dpi=120)
    plt.close(fig)
    _wrap_as_html(png_path, "GDP per capita vs CO2 per capita (Matplotlib, static)")


if __name__ == "__main__":
    line_chart()
    bubble_chart()
    print("Saved: output/matplotlib_line.{png,html}, output/matplotlib_bubble.{png,html}")
    print("Both formats are flat images: no hover, no zoom, no pan, no legend")
    print("toggle — the .html wrapper is only for side-by-side comparison with")
    print("plotly_line.html / plotly_bubble.html, not a source of interactivity.")
