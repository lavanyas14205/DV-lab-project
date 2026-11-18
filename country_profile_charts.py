"""Chart builder for the Country Climate Profile page (pages/country_profile.py)."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots


def country_trend_sparklines(series_by_label: dict) -> go.Figure:
    """One small line chart per non-empty {label: DataFrame[year, value]} entry.

    A country missing one metric entirely (e.g. no GDP data) just gets fewer
    subplots rather than an empty/broken one. A country with no metrics at all
    returns an empty figure with an informational message.
    """
    items = [(label, series) for label, series in series_by_label.items() if not series.empty]

    # Guard: all series are empty
    if not items:
        fig = go.Figure()
        fig.add_annotation(
            text="No trend data available for this country",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
        )
        return fig

    fig = make_subplots(rows=1, cols=len(items), subplot_titles=[label for label, _ in items])
    for i, (_, series) in enumerate(items, start=1):
        fig.add_trace(
            go.Scatter(x=series["year"], y=series["value"], mode="lines", showlegend=False),
            row=1, col=i,
        )
    fig.update_layout(height=300, margin=dict(t=60, b=30), title="Trend, 1990-present")
    return fig
