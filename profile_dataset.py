"""Reproduces the dataset profile behind the cleaning rules in CLAUDE.md.

This is graded evidence for Week 3: run it and the printed numbers should
match the ones cited in CLAUDE.md's cleaning-rules section. It only reads
and reports — all cleaning itself lives in data/, not here.
"""

import data


def profile_entities(co2_all, co2_countries):
    n_entities = co2_all["country"].nunique()
    n_countries = co2_countries["country"].nunique()
    n_aggregates = n_entities - n_countries
    print(f"Entities total: {n_entities}")
    print(f"  Real countries (ISO-3 code): {n_countries}")
    print(f"  Aggregates (no ISO-3 code): {n_aggregates}")
    print(f"Year range: {co2_all['year'].min()}-{co2_all['year'].max()}")
    print(f"Rows x columns: {co2_all.shape[0]} x {co2_all.shape[1]}")


def profile_gdp(co2_countries):
    print(f"\nGDP last reported year: {co2_countries.loc[co2_countries['gdp'].notna(), 'year'].max()}")
    recent = data.cap_year(co2_countries[co2_countries["year"] >= data.DEFAULT_YEAR_RANGE[0]])
    print(f"GDP missing, {data.DEFAULT_YEAR_RANGE[0]}-{data.GDP_MAX_YEAR}: {recent['gdp'].isna().mean():.0%}")


def profile_sparse_emissions(co2_countries):
    recent = co2_countries[co2_countries["year"].between(*data.DEFAULT_YEAR_RANGE)]
    print(f"\nSparse emissions columns, {data.DEFAULT_YEAR_RANGE[0]}-{data.DEFAULT_YEAR_RANGE[1]}:")
    for col in data.SPARSE_EMISSIONS_COLUMNS:
        print(f"  {col}: {recent[col].isna().mean():.0%} missing")


def profile_population(co2_countries):
    latest_year = co2_countries["year"].max()
    latest = co2_countries[co2_countries["year"] == latest_year]
    n_small = (latest["population"] < data.MIN_POPULATION_FOR_PER_CAPITA).sum()
    print(f"\nCountries under {data.MIN_POPULATION_FOR_PER_CAPITA:,} population ({latest_year}): {n_small}")


def profile_energy(energy_all):
    from data.co2 import filter_countries
    from data.energy import ENERGY_MAX_YEAR

    countries = filter_countries(energy_all)
    latest = countries[countries["year"] == ENERGY_MAX_YEAR]
    print(f"\nEnergy dataset, {ENERGY_MAX_YEAR}:")
    print(f"  renewables_share_energy non-null: {latest['renewables_share_energy'].notna().sum()} / {len(latest)}")
    print(f"  renewables_share_elec non-null: {latest['renewables_share_elec'].notna().sum()} / {len(latest)} (rule 7: use this one)")


def main():
    loaded = data.load_all()
    co2_all, co2_countries, temperature = loaded.co2_all, loaded.co2_countries, loaded.temperature
    profile_entities(co2_all, co2_countries)
    profile_gdp(co2_countries)
    profile_sparse_emissions(co2_countries)
    profile_population(co2_countries)
    profile_energy(loaded.energy)
    print(f"\nGISTEMP rows: {len(temperature)}, "
          f"years {temperature['year'].min()}-{temperature['year'].max()}")


if __name__ == "__main__":
    main()
