import pandas as pd

from country_profile_charts import country_trend_sparklines


def test_country_trend_sparklines_makes_one_subplot_per_nonempty_series():
    series_by_label = {
        "CO2 (Mt)": pd.DataFrame({"year": [2000, 2001], "value": [1.0, 2.0]}),
        "GDP/person ($)": pd.DataFrame({"year": [], "value": []}),  # e.g. a country with no GDP data
        "Renewables (%)": pd.DataFrame({"year": [2000, 2001], "value": [10.0, 12.0]}),
    }

    fig = country_trend_sparklines(series_by_label)

    subplot_titles = [ann["text"] for ann in fig.layout.annotations]
    assert subplot_titles == ["CO2 (Mt)", "Renewables (%)"]
    assert len(fig.data) == 2


def test_country_trend_sparklines_returns_empty_figure_when_all_series_empty():
    series_by_label = {
        "CO2 (Mt)": pd.DataFrame({"year": [], "value": []}),
        "GDP/person ($)": pd.DataFrame({"year": [], "value": []}),
        "Renewables (%)": pd.DataFrame({"year": [], "value": []}),
    }

    fig = country_trend_sparklines(series_by_label)

    # No traces for empty figure
    assert len(fig.data) == 0
    # Should have exactly one annotation with the message
    assert len(fig.layout.annotations) == 1
    assert fig.layout.annotations[0]["text"] == "No trend data available for this country"
