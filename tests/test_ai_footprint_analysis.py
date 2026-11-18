import pandas as pd

from ai_footprint_analysis import bucket_prompt, per_capita_share


def _footprint_fixture():
    """A minimal footprint frame with the (use_case, word_count_max) shape
    bucket_prompt reads -- duplicated across two models, same as the real
    16-row table, to prove drop_duplicates handles that correctly."""
    return pd.DataFrame({
        "model": ["ChatGPT", "Claude"] * 4,
        "use_case": [
            "simple_qa", "simple_qa",
            "email_summary", "email_summary",
            "document_review", "document_review",
            "coding_agent", "coding_agent",
        ],
        "word_count_max": [15, 15, 60, 60, 200, 200, 100000, 100000],
    })


def _words(n):
    return " ".join(["word"] * n)


def test_bucket_prompt_at_lower_boundary_word_count():
    result = bucket_prompt(_words(15), _footprint_fixture())
    assert result == "simple_qa"


def test_bucket_prompt_one_word_over_boundary_moves_to_next_bucket():
    result = bucket_prompt(_words(16), _footprint_fixture())
    assert result == "email_summary"


def test_bucket_prompt_at_email_summary_upper_boundary():
    result = bucket_prompt(_words(60), _footprint_fixture())
    assert result == "email_summary"


def test_bucket_prompt_at_document_review_boundary():
    result = bucket_prompt(_words(200), _footprint_fixture())
    assert result == "document_review"


def test_bucket_prompt_far_over_document_review_falls_into_coding_agent():
    result = bucket_prompt(_words(201), _footprint_fixture())
    assert result == "coding_agent"


def test_bucket_prompt_empty_string_returns_none():
    assert bucket_prompt("", _footprint_fixture()) is None


def test_bucket_prompt_whitespace_only_returns_none():
    assert bucket_prompt("   ", _footprint_fixture()) is None


def test_per_capita_share_computes_percentage_of_annual_country_co2():
    # 1,000,000 g = 1 tonne; 1 / 5.0 tonnes = 20%
    result = per_capita_share(1_000_000, 5.0)
    assert result == 20.0


def test_per_capita_share_returns_none_when_country_value_is_missing():
    assert per_capita_share(1_000_000, None) is None


def test_per_capita_share_returns_none_when_country_value_is_zero():
    assert per_capita_share(1_000_000, 0.0) is None


def test_per_capita_share_returns_zero_for_zero_usage():
    assert per_capita_share(0, 5.0) == 0.0


def test_equivalents_converts_to_everyday_units():
    from ai_footprint_analysis import equivalents
    result = equivalents(energy_wh=120, co2_g=250, water_ml=500)
    assert result["led_hours"] == 12
    assert result["phone_charges"] == 10
    assert result["car_metres"] == 1000
    assert result["water_glasses"] == 2


def test_grid_co2_scales_with_intensity():
    from ai_footprint_analysis import grid_co2_g
    assert grid_co2_g(1000, 500) == 500
    assert grid_co2_g(0, 500) == 0


def test_scenario_intensity_starts_at_today_and_falls_with_more_renewables():
    from ai_footprint_analysis import RENEWABLE_G_PER_KWH, scenario_intensity
    assert abs(scenario_intensity(400, 40, 40) - 400) < 1e-9
    assert scenario_intensity(400, 40, 100) == RENEWABLE_G_PER_KWH
    assert scenario_intensity(400, 40, 80) < scenario_intensity(400, 40, 60) < 400


def test_scenario_intensity_handles_fully_renewable_country():
    from ai_footprint_analysis import scenario_intensity
    # no fossil intensity can be inferred at 100% renewable -> fallback, still finite
    assert scenario_intensity(25, 100, 50) > 25
