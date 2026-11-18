"""Reads the NASA POWER solar/wind climatology cache — see
scripts/build_climatology_cache.py for how it's built. No network code
here or anywhere in the running app; this only reads a checked-in file.
"""

from pathlib import Path

import pandas as pd

CLIMATOLOGY_PATH = str(Path(__file__).resolve().parent / "power_climatology.csv")


def load_climatology_data(path: str = CLIMATOLOGY_PATH) -> pd.DataFrame:
    return pd.read_csv(path)
