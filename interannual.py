from network import *
from plotter import *

years = [2015, 2016, 2017] # the three years the load and cf data overlap

capacity_results = []

for year in years:

    print(f"Running model for {year}")

    load, wind_cf, solar_cf = load_data("EE", year)

    hours = pd.date_range(
        f'{year}-01-01 00:00Z',
        f'{year}-12-31 23:00Z',
        freq='h'
    )

    network = Network(load, wind_cf, solar_cf, hours)
    network.build_network()
    network.optimize_network()

    _, capacities = network.display_results()

    capacity_results.append(capacities)

capacity_df = pd.DataFrame(capacity_results, index=years)

#print(capacity_df)

avg_capacity = capacity_df.mean()
std_capacity = capacity_df.std()
plot_capacity_variability(capacity_df)