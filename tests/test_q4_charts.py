import pandas as pd

from q4_charts import outlier_details, top_extremes, trend_residuals


def test_trend_residuals_is_zero_for_points_exactly_on_the_line():
    x = pd.Series([1.0, 2.0, 3.0])
    y = pd.Series([2.0, 4.0, 6.0])  # y = 2x, perfectly linear

    result = trend_residuals(x, y)

    assert all(abs(r) < 1e-9 for r in result)


def test_top_extremes_returns_furthest_above_and_below_the_trend():
    countries = pd.Series(["A", "B", "C", "D"])
    residuals = pd.Series([-10.0, 1.0, 2.0, 10.0])

    result = top_extremes(countries, residuals, n=1)

    assert result == ["A", "D"]


def test_outlier_details_returns_top_and_bottom_by_residual():
    energy_df = pd.DataFrame({
        "iso_code": ["AAA", "BBB", "CCC", "DDD"],
        "country": ["A", "B", "C", "D"],
        "population": [1_000_000] * 4,
        "renewables_share_elec": [1.0, 20.0, 30.0, 90.0],
    })
    climatology_df = pd.DataFrame({
        "iso_code": ["AAA", "BBB", "CCC", "DDD"],
        "solar_kwh_per_m2_day": [1.0, 2.0, 3.0, 4.0],
    })

    result = outlier_details(energy_df, climatology_df, potential="solar", n=1)

    # Verified against np.polyfit on this exact data: residuals are
    # A=+7.3, B=-1.4, C=-19.1, D=+13.2. D is furthest above the trend
    # (leader); C is furthest below (under-utiliser) — not A, which is
    # actually above the line despite its low absolute share.
    assert result["leaders"][0]["country"] == "D"
    assert result["under_utilisers"][0]["country"] == "C"
    assert set(result["leaders"][0].keys()) == {
        "country", "solar_kwh_per_m2_day", "renewables_share_elec", "residual",
    }
    assert result["leaders"][0]["residual"] > result["under_utilisers"][0]["residual"]
