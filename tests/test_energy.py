import pandas as pd

from data.energy import RENEWABLE_SHARE_COLUMN, renewable_share


def test_renewable_share_reads_the_electricity_column_not_total_energy_column():
    """Rule 7: renewables_share_energy is non-null for only 79/220 countries
    and doesn't vary by year in the live file — renewables_share_elec covers
    210-212/220 and is the one that should ever reach a chart."""
    df = pd.DataFrame(
        {
            "renewables_share_elec": [80.0],
            "renewables_share_energy": [10.0],
        }
    )

    result = renewable_share(df)

    assert result.iloc[0] == 80.0
    assert RENEWABLE_SHARE_COLUMN == "renewables_share_elec"
