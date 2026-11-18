from scripts.build_climatology_cache import extract_annual_values


def test_extract_annual_values_reads_ann_field_from_power_response():
    """Shape confirmed live against NASA POWER's climatology endpoint:
    https://power.larc.nasa.gov/api/temporal/climatology/point
      ?parameters=ALLSKY_SFC_SW_DWN,WS10M&community=RE&longitude=...&latitude=...&format=JSON
    """
    response = {
        "properties": {
            "parameter": {
                "ALLSKY_SFC_SW_DWN": {"JAN": 2.173, "FEB": 2.969, "ANN": 4.1196},
                "WS10M": {"JAN": 4.65, "FEB": 4.72, "ANN": 3.97},
            }
        }
    }

    solar, wind = extract_annual_values(response)

    assert solar == 4.1196
    assert wind == 3.97
