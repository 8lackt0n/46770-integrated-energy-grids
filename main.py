import pandas as pd
from data_loader import load_data
from plotter import *
from network import Network

### LOADING DATA ###

print("Loading data...")
load, wind_cf, solar_cf = load_data(year=2017)

print(f"Load series length: {len(load)}")
print(f"Wind CF series length: {len(wind_cf)}")
print(f"Solar CF series length: {len(solar_cf)}")
hours = pd.date_range('2017-01-01 00:00','2017-12-31 23:00',freq='h')

# a), b) and c)

january_week_mask = (hours >= '2017-01-01') & (hours < '2017-01-08')
january_week = hours[january_week_mask]

july_week_mask = (hours >= '2017-07-01') & (hours < '2017-07-08')
july_week = hours[july_week_mask]

scenarios = [(False, "without storage"),(True, "with storage"),]

for storage_enabled, scenario_label in scenarios:
    network = Network(load, wind_cf, solar_cf, hours)
    network.build_network(storage=storage_enabled)
    network.optimize_network()
    dispatch, _, storage_data = network.display_results()

    plot_dispatch(
            january_week,
            dispatch[january_week_mask],
            load['EE'][january_week_mask],
            f"Optimal Hourly Dispatch for One Week in January 2017 ({scenario_label})",
            )

    plot_dispatch(
        july_week,
        dispatch[july_week_mask],
        load['EE'][july_week_mask],
        f"Optimal Hourly Dispatch for One Week in July 2017 ({scenario_label})",
        )


    plot_annual_energy_mix(dispatch, f"Annual Energy Mix for 2017 ({scenario_label})")
    plot_duration_curve(dispatch, f"Duration Curve for 2017 ({scenario_label})")

    if storage_data is not None:
        plot_storage_operation(
                        january_week,
                        storage_data[january_week_mask],
                        f"Battery Storage Operation for One Week in January 2017 ({scenario_label})",
                        )
    
        plot_storage_operation(
                    july_week,
                    storage_data[july_week_mask],
                    f"Battery Storage Operation for One Week in July 2017 ({scenario_label})",
                    )


# d)
network = Network(load, wind_cf, solar_cf, hours)
network.build_network(storage=True, transmission=True, external=True)
network.optimize_network()
dispatch, capacities, storage_data = network.display_results()
# TODO: Maybe add more generation technologies
# TODO: Plot and discuss the results

# e)

# dispatch the first hour
dispatch_first_hour = dispatch.iloc[0]
print("Dispatch for the first hour of 2017:")
print(dispatch_first_hour)