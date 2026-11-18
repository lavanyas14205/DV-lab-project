import pandas as pd

from data.gistemp import load_temperature_data, parse_gistemp


def test_parse_gistemp_renames_and_selects_annual_column():
    raw = pd.DataFrame(
        {
            "Year": [1880, 1881],
            "Jan": [-0.19, -0.20],
            "J-D": ["-.17", "-.09"],
        }
    )

    result = parse_gistemp(raw)

    assert list(result.columns) == ["year", "temperature_anomaly"]
    assert list(result["year"]) == [1880, 1881]


def test_parse_gistemp_coerces_asterisk_placeholders_to_nan():
    raw = pd.DataFrame({"Year": [2024, 2025], "J-D": ["1.20", "***"]})

    result = parse_gistemp(raw)

    assert result["temperature_anomaly"].iloc[0] == 1.20
    assert pd.isna(result["temperature_anomaly"].iloc[1])


def test_load_temperature_data_skips_gistemp_preamble_line(tmp_path):
    csv_text = (
        "Land-Ocean: Global Means\n"
        "Year,Jan,J-D\n"
        "1880,-.19,-.17\n"
        "1881,-.20,-.09\n"
    )
    path = tmp_path / "gistemp.csv"
    path.write_text(csv_text)

    result = load_temperature_data(str(path))

    assert list(result["year"]) == [1880, 1881]
    assert list(result["temperature_anomaly"]) == [-0.17, -0.09]
