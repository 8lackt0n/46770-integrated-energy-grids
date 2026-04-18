from network import *
from plotter import *

years = [2015, 2016, 2017]

capacity_results = []

base_load, _, _ = load_data(2016)

for year in years:
    print(f"Running model for {year}")

    _, wind_cf, solar_cf = load_data(year)

    hours = pd.date_range(
        f"{year}-01-01 00:00Z",
        f"{year}-12-31 23:00Z",
        freq="h"
    )

    if year == 2016:
        load_year = base_load.copy()
    else:
        load_year = base_load[~((base_load.index.month == 2) & (base_load.index.day == 29))].copy()

    load_year = load_year.copy()
    load_year.index = hours

    print(len(load_year), len(wind_cf), len(solar_cf), len(hours))

    network = Network(load_year, wind_cf, solar_cf, hours)
    network.build_network()
    network.optimize_network()

    _, capacities, _, _, _ = network.display_results()
    capacity_results.append(capacities)

capacity_df = pd.DataFrame(capacity_results, index=years)

avg_capacity = capacity_df.mean()
std_capacity = capacity_df.std()
plot_capacity_variability(capacity_df, "Average Generator Capacity with Weather Variability")
