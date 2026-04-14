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

# a) and c) (see interannual for b))

january_week_mask = (hours >= '2017-01-01') & (hours < '2017-01-08')
january_week = hours[january_week_mask]

july_week_mask = (hours >= '2017-07-01') & (hours < '2017-07-08')
july_week = hours[july_week_mask]

scenarios = [(False, "without storage"),(True, "with storage"),]

scenario_results = []


def compute_shared_power_axis_max(dispatch_df, load_series):
    # Support both single-node names and Estonia-specific names.
    dispatch_power_columns = [
        "Wind Generator",
        "Wind Generator Estonia",
        "Solar Generator",
        "Solar Generator Estonia",
        "OCGT",
        "OCGT Estonia",
        "Coal",
        "Coal Estonia",
        "Battery Storage Discharge",
    ]

    power_max_candidates = [float(load_series.max())]
    available_columns = [col for col in dispatch_power_columns if col in dispatch_df.columns]
    if available_columns:
        total_power = dispatch_df[available_columns].sum(axis=1)
        power_max_candidates.append(float(total_power.max()))

    return max(power_max_candidates) * 1.05

for storage_enabled, scenario_label in scenarios:
    network = Network(load, wind_cf, solar_cf, hours)
    network.build_network(storage=storage_enabled)
    network.optimize_network()
    dispatch, _, storage_data, battery_capacity, _ = network.display_results()

    scenario_results.append(
        {
            "storage_enabled": storage_enabled,
            "scenario_label": scenario_label,
            "dispatch": dispatch,
            "storage_data": storage_data,
            "battery_capacity": battery_capacity,
        }
    )

shared_power_axis_max = max(
    compute_shared_power_axis_max(result["dispatch"], load["EE"])
    for result in scenario_results
)

january_week_mask = (hours >= '2017-01-01') & (hours < '2017-01-08')
january_week = hours[january_week_mask]

july_week_mask = (hours >= '2017-07-01') & (hours < '2017-07-08')
july_week = hours[july_week_mask]

load_est = load["EE"]

for result in scenario_results:
    storage_enabled = result["storage_enabled"]
    scenario_label = result["scenario_label"]
    dispatch = result["dispatch"]
    storage_data = result["storage_data"]
    battery_capacity = result["battery_capacity"]

    plot_dispatch(
        january_week,
        dispatch[january_week_mask],
        load_est[january_week_mask],
        f"Optimal Hourly Dispatch for One Week in January 2017 ({scenario_label})",
        power_axis_max=shared_power_axis_max,
        soc_axis_max=battery_capacity,
    )

    plot_dispatch(
        july_week,
        dispatch[july_week_mask],
        load_est[july_week_mask],
        f"Optimal Hourly Dispatch for One Week in July 2017 ({scenario_label})",
        power_axis_max=shared_power_axis_max,
        soc_axis_max=battery_capacity,
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

dispatch, capacities, storage_data, battery_capacity, dispatch_all = network.display_results()

january_week_mask = (hours >= '2017-01-01') & (hours < '2017-01-08')
january_week = hours[january_week_mask]

july_week_mask = (hours >= '2017-07-01') & (hours < '2017-07-08')
july_week = hours[july_week_mask]

load_est = load["EE"]

scenario_label = "with storage and transmission"

shared_power_axis_max = compute_shared_power_axis_max(dispatch, load_est)

# --- PLOTS ---
plot_dispatch(
    january_week,
    dispatch[january_week_mask],
    load_est[january_week_mask],
    f"Optimal Hourly Dispatch for One Week in January 2017 ({scenario_label})",
    power_axis_max=shared_power_axis_max,
    soc_axis_max=battery_capacity,
)

plot_dispatch(
    july_week,
    dispatch[july_week_mask],
    load_est[july_week_mask],
    f"Optimal Hourly Dispatch for One Week in July 2017 ({scenario_label})",
    power_axis_max=shared_power_axis_max,
    soc_axis_max=battery_capacity,
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



# e)
# calculate imbalances in each node for the first hour
# Finland
generation_finland = dispatch_all['Wind Generator Finland'].iloc[0] + dispatch_all['Nuclear Finland'].iloc[0]
imbalance_finland = generation_finland - load['FI'].iloc[0]
# Sweden (SE2)
generation_sweden = dispatch_all['Wind Generator Sweden'].iloc[0] + dispatch_all['Hydro Sweden'].iloc[0]
imbalance_sweden = generation_sweden - load['SE'].iloc[0]
# Latvia
generation_latvia = dispatch_all['Wind Generator Latvia'].iloc[0] + dispatch_all['Coal Latvia'].iloc[0]
imbalance_latvia = generation_latvia - load['LV'].iloc[0]

generation_estonia = dispatch_all['Wind Generator Estonia'].iloc[0] + dispatch_all['Coal Estonia'].iloc[0] + dispatch_all['Solar Generator Estonia'].iloc[0] + dispatch_all['OCGT Estonia'].iloc[0] + dispatch['Battery Storage Discharge'].iloc[0]
imbalance_estonia = generation_estonia - (load['EE'].iloc[0] + dispatch['Battery Storage Charge'].iloc[0])


# create dataframe for imbalances
imbalance_df = pd.DataFrame({
    "Finland": imbalance_finland,
    "Sweden": imbalance_sweden,
    "Latvia": imbalance_latvia,
    "Estonia": imbalance_estonia
}, index=[dispatch.index[0]])
print("Imbalances in each node for the first hour:")
print(imbalance_df)

# print power flows in each line for the first hour
print("Power flows in each line for the first hour:")
print(network.network.lines_t.p0.loc[network.network.snapshots[0]])

# f) Carbon emission analysis

scenario_results = network.global_carbon_analysis()

plot_annual_energy_mix_vs_co2_limits(scenario_results, f"Annual Energy Mix for 2017 under Different CO2 Emission Limits", show=False, save=True)

# g) Add gas transmission network
network.build_network(storage=True, transmission=True, external=True, gas_transmission=True)

network.optimize_network()

dispatch, capacities, storage_data, battery_capacity, dispatch_all = network.display_results()

# plot energy mix with gas transmission
plot_annual_energy_mix(dispatch, f"Annual Energy Mix for 2017 with Gas Transmission", show=False, save=True)

# h) Add carbon emission constraints
network.build_network(storage=True, transmission=True, external=True, gas=True, co2_limit=True, limit=28_000_000 * 0.01)

network.optimize_network()

co2_price = network.network.global_constraints.mu
print(co2_price)