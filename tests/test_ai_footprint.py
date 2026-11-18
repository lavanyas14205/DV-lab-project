from pathlib import Path

import pandas as pd

from data.ai_footprint import load_ai_footprint_data

AI_FOOTPRINT_CSV = Path(__file__).resolve().parent.parent / "data" / "ai_footprint.csv"


def test_load_ai_footprint_data_reads_expected_columns(tmp_path):
    csv_text = (
        "model,use_case,energy_wh,co2_g,water_ml,word_count_max,source\n"
        "ChatGPT,simple_qa,0.16,0.04,0.32,15,test\n"
    )
    path = tmp_path / "ai_footprint.csv"
    path.write_text(csv_text)

    result = load_ai_footprint_data(str(path))

    assert list(result.columns) == [
        "model", "use_case", "energy_wh", "co2_g", "water_ml", "word_count_max", "source",
    ]
    assert result.iloc[0]["model"] == "ChatGPT"
    assert result.iloc[0]["energy_wh"] == 0.16


def _load_real_csv():
    return pd.read_csv(AI_FOOTPRINT_CSV)


def test_ai_footprint_csv_has_expected_columns():
    df = _load_real_csv()
    assert list(df.columns) == [
        "model", "use_case", "energy_wh", "co2_g", "water_ml", "word_count_max", "source",
    ]


def test_ai_footprint_csv_has_all_sixteen_model_use_case_combinations():
    df = _load_real_csv()
    expected_models = {"ChatGPT", "Claude", "Gemini", "Grok"}
    expected_use_cases = {"simple_qa", "email_summary", "document_review", "coding_agent"}
    assert set(df["model"]) == expected_models
    assert set(df["use_case"]) == expected_use_cases
    assert len(df) == 16
    assert not df.duplicated(subset=["model", "use_case"]).any()


def test_ai_footprint_csv_has_no_missing_footprint_values():
    df = _load_real_csv()
    assert df[["energy_wh", "co2_g", "water_ml"]].notna().all().all()


def test_ai_footprint_csv_word_count_max_is_consistent_within_each_use_case():
    """Every model's row for a given use_case must share the same
    word_count_max -- ai_footprint_analysis.bucket_prompt() (Task 4)
    de-duplicates on (use_case, word_count_max) and would silently pick an
    arbitrary one if they disagreed."""
    df = _load_real_csv()
    per_use_case = df.groupby("use_case")["word_count_max"].nunique()
    assert (per_use_case == 1).all()
