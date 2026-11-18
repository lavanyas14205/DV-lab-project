"""NASA GISTEMP v4 loading and parsing."""

import pandas as pd

GISTEMP_URL = "https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv"


def parse_gistemp(raw: pd.DataFrame) -> pd.DataFrame:
    """Turn a raw (already skiprows=1) GISTEMP frame into (year, anomaly).

    Missing values are written as "*" in the source file, so J-D must be
    coerced rather than read as numeric directly.
    """
    out = raw[["Year", "J-D"]].rename(
        columns={"Year": "year", "J-D": "temperature_anomaly"}
    )
    out["temperature_anomaly"] = pd.to_numeric(
        out["temperature_anomaly"], errors="coerce"
    )
    return out


def load_temperature_data(path_or_url: str = GISTEMP_URL) -> pd.DataFrame:
    # One preamble line above the header row.
    raw = pd.read_csv(path_or_url, skiprows=1)
    return parse_gistemp(raw)
