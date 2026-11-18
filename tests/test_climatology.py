from data.climatology import load_climatology_data


def test_load_climatology_data_reads_iso_code_solar_and_wind_columns(tmp_path):
    csv_text = (
        "iso_code,solar_kwh_per_m2_day,wind_speed_ms\n"
        "USA,4.12,3.97\n"
        "ISL,2.05,6.31\n"
    )
    path = tmp_path / "power_climatology.csv"
    path.write_text(csv_text)

    result = load_climatology_data(str(path))

    assert list(result.columns) == ["iso_code", "solar_kwh_per_m2_day", "wind_speed_ms"]
    assert list(result["iso_code"]) == ["USA", "ISL"]
