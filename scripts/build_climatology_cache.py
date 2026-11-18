"""One-time, offline: fetch solar/wind climatology for every capital in
data/capitals.csv from NASA POWER, cache to data/power_climatology.csv.

Run manually: python scripts/build_climatology_cache.py
Never invoked by the deployed app — data/climatology.py only ever reads
the cache file this script produces, so the running app makes zero calls
to NASA, at startup or otherwise.

Uses only the standard library (urllib, csv, json) — this script is not a
runtime dependency of the app, so it doesn't need `requests` added to
requirements.txt.
"""

import csv
import json
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPITALS_PATH = REPO_ROOT / "data" / "capitals.csv"
CACHE_PATH = REPO_ROOT / "data" / "power_climatology.csv"

POWER_URL = (
    "https://power.larc.nasa.gov/api/temporal/climatology/point"
    "?parameters=ALLSKY_SFC_SW_DWN,WS10M&community=RE"
    "&longitude={lon}&latitude={lat}&format=JSON"
)

FIELDNAMES = ["iso_code", "solar_kwh_per_m2_day", "wind_speed_ms"]


def extract_annual_values(power_response: dict) -> tuple:
    """Pull annual solar irradiance and wind speed from a POWER climatology response."""
    params = power_response["properties"]["parameter"]
    solar = params["ALLSKY_SFC_SW_DWN"]["ANN"]
    wind = params["WS10M"]["ANN"]
    return solar, wind


def fetch_climatology(lat: float, lon: float) -> tuple:
    url = POWER_URL.format(lat=lat, lon=lon)
    with urllib.request.urlopen(url, timeout=30) as response:
        payload = json.loads(response.read())
    return extract_annual_values(payload)


def load_capitals() -> list:
    with open(CAPITALS_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_existing_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    with open(CACHE_PATH, newline="", encoding="utf-8") as f:
        return {row["iso_code"]: row for row in csv.DictReader(f)}


def main():
    capitals = load_capitals()
    cached = load_existing_cache()

    with open(CACHE_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

        for row in cached.values():
            writer.writerow(row)

        for entry in capitals:
            iso_code = entry["iso_code"]
            if iso_code in cached:
                continue
            try:
                solar, wind = fetch_climatology(float(entry["lat"]), float(entry["lon"]))
            except Exception as exc:
                print(f"SKIP {iso_code} ({entry['capital']}): {exc}")
                continue
            writer.writerow(
                {"iso_code": iso_code, "solar_kwh_per_m2_day": solar, "wind_speed_ms": wind}
            )
            f.flush()
            print(f"OK {iso_code} ({entry['capital']}): solar={solar} wind={wind}")
            time.sleep(0.2)


if __name__ == "__main__":
    main()
