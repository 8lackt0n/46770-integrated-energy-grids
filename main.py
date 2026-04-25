import pandas as pd
from data_loader import load_data
from plotter import *
from network import Network
from helper import *

### LOADING DATA ###

print("Loading data...")
load, wind_cf, solar_cf = load_data(year=2017)

print(f"Load series length: {len(load)}")
print(f"Wind CF series length: {len(wind_cf)}")
print(f"Solar CF series length: {len(solar_cf)}")
hours = pd.date_range('2017-01-01 00:00','2017-12-31 23:00',freq='h')

january_week_mask = (hours >= '2017-01-01') & (hours < '2017-01-08')
january_week = hours[january_week_mask]

july_week_mask = (hours >= '2017-07-01') & (hours < '2017-07-08')
july_week = hours[july_week_mask]

load_est = load["EE"]

### ANALYSIS ###

# a) and c) (see interannual for b))


scenarios = [(False, "without storage"),(True, "with storage"),]

scenario_results = []


for storage_enabled, scenario_label in scenarios:
    network = Network(load, wind_cf, solar_cf, hours)
    network.build_network(storage=storage_enabled)
    network.optimize_network()
    dispatch, capacities = network.save_results()
    scenario_results.append(
        {
            "storage_enabled": storage_enabled,
            "scenario_label": scenario_label,
            "dispatch": dispatch,
            "capacities": capacities,
            "soc_axis_max": capacities.get('Battery Storage Estonia', 0) if storage_enabled else 0
        }
    )

shared_power_axis_max = max(
    compute_shared_power_axis_max(result["dispatch"], load["EE"])
    for result in scenario_results)


for result in scenario_results:
    storage_enabled = result["storage_enabled"]
    scenario_label = result["scenario_label"]
    dispatch = result["dispatch"]
    capacities = result["capacities"]
    soc_axis_max = result["soc_axis_max"]
    
    plot_capacity_mix(capacities, f"Optimal Installed Capacity Mix for Estonia 2017 ({scenario_label})")
    plot_annual_energy_mix(dispatch, f"Annual Energy Mix for Estonia 2017 ({scenario_label})")
    
    plot_dispatch(
        january_week,
        dispatch[january_week_mask],
        load_est[january_week_mask],
        f"Optimal Hourly Dispatch for One Week in January 2017 ({scenario_label})", 
        power_axis_max=shared_power_axis_max,
        soc_axis_max=soc_axis_max
    )
    
    plot_dispatch(
        july_week,
        dispatch[july_week_mask],
        load_est[july_week_mask],
        f"Optimal Hourly Dispatch for One Week in July 2017 ({scenario_label})",
        power_axis_max=shared_power_axis_max,
        soc_axis_max=soc_axis_max
    )
    
    plot_capacity_mix(capacities, f"Optimal Installed Capacity Mix for Estonia 2017 ({scenario_label})")
    plot_annual_energy_mix(dispatch, f"Annual Energy Mix for Estonia 2017 ({scenario_label})")      
    plot_duration_curve(dispatch, f"Duration Curve for 2017 ({scenario_label})")
    

    if storage_enabled:
        plot_storage_operation(
            january_week,
            dispatch[january_week_mask],
            f"Battery Storage Operation for One Week in January 2017 ({scenario_label})",
        )
        plot_storage_operation(
            july_week,
            dispatch[july_week_mask],
            f"Battery Storage Operation for One Week in July 2017 ({scenario_label})",
        )

# d)
network = Network(load, wind_cf, solar_cf, hours)

network.build_network(storage=True, transmission=True, external=True)

network.optimize_network()

dispatch, capacities = network.save_results()

soc_max = capacities.get('Battery Storage Estonia', 0)

scenario_label = "with storage and transmission"

shared_power_axis_max = compute_shared_power_axis_max(dispatch, load_est)

#--- PLOTS ---
plot_dispatch_with_net_transmission(
    january_week,
    dispatch[january_week_mask],
    load_est[january_week_mask],
    f"Optimal Hourly Dispatch for One Week in January 2017 ({scenario_label})",
    power_axis_max=shared_power_axis_max,
    soc_axis_max=soc_max,
)

plot_dispatch_with_net_transmission(
    july_week,
    dispatch[july_week_mask],
    load_est[july_week_mask],
    f"Optimal Hourly Dispatch for One Week in July 2017 ({scenario_label})",
    power_axis_max=shared_power_axis_max,
    soc_axis_max=soc_max,
)

plot_capacity_mix_by_country(capacities, f"Optimal Installed Capacity Mix by Country 2017 ({scenario_label})", show=False, save=True)
plot_annual_energy_mix(dispatch, f"Annual Energy Mix for Estonia 2017 ({scenario_label})", show=False, save=True)
plot_duration_curve(dispatch, f"Duration Curve for 2017 ({scenario_label})")


plot_storage_operation(
    january_week,
    dispatch[january_week_mask],
    f"Battery Storage Operation for One Week in January 2017 ({scenario_label})",
    )
plot_storage_operation(
    july_week,
    dispatch[july_week_mask],
    f"Battery Storage Operation for One Week in July 2017 ({scenario_label})",
    )



# e)
# calculate imbalances in each node for the first hour
# Finland
generation_finland = dispatch['Wind Generator Finland'].iloc[0] + dispatch['Nuclear Finland'].iloc[0]
imbalance_finland = generation_finland - load['FI'].iloc[0]
# Sweden (SE2)
generation_sweden = dispatch['Wind Generator Sweden'].iloc[0] + dispatch['Hydro Sweden'].iloc[0]
imbalance_sweden = generation_sweden - load['SE'].iloc[0]
# Latvia
generation_latvia = dispatch['Wind Generator Latvia'].iloc[0] + dispatch['Coal Latvia'].iloc[0]
imbalance_latvia = generation_latvia - load['LV'].iloc[0]

generation_estonia = dispatch['Wind Generator Estonia'].iloc[0] + dispatch['Coal Estonia'].iloc[0] + dispatch['Solar Generator Estonia'].iloc[0] + dispatch['OCGT Estonia'].iloc[0] + dispatch['Battery Discharge Estonia'].iloc[0]
imbalance_estonia = generation_estonia - (load['EE'].iloc[0] + dispatch['Battery Charge Estonia'].iloc[0])


# create dataframe for imbalances
imbalance_df = pd.DataFrame({
    "Finland": imbalance_finland,
    "Sweden": imbalance_sweden,
    "Latvia": imbalance_latvia,
    "Estonia": imbalance_estonia
}, index=[dispatch.index[0]])
print("--------------------------------------------------------")

print("Imbalances in each node for the first hour:")
print(imbalance_df)

# print power flows in each line for the first hour
print("Power flows in each line for the first hour:")
print(network.network.lines_t.p0.loc[network.network.snapshots[0]])
print("--------------------------------------------------------")


# f) CO2 limit analysis
# https://kliimaministeerium.ee/sites/default/files/documents/2024-04/Energy%20summary_2024.pdf?
base_co2 = 28_000_000
    
    
scenario_results = []
    
co2_limits = [base_co2, 0.2 * base_co2, 0.1 * base_co2, 0.05 * base_co2] # in tons of CO2
    
for co2_limit in co2_limits:
    network = Network(load, wind_cf, solar_cf, hours=hours)
        
    network.build_network(storage=True)
        
    network.add_co2_limit(co2_limit)
        
    network.optimize_network()
        
    _, capacities = network.save_results()
        
    scenario_results.append(
            {
                "co2_limit": co2_limit,
                "capacities": capacities,
            }
        )

plot_capacities_vs_co2_limits(scenario_results, f"Installed Capacities under Different CO2 Emission Limits Estonia, 2017", show=False, save=True)

# g) Add gas transmission network

network = Network(load,wind_cf, solar_cf, hours=hours)

network.build_network(storage=True, transmission=True, external=True, gas=True)

network.optimize_network()

dispatch, capacities = network.save_results()

plot_total_transmission_comparison(dispatch, title="Total Transported Energy in 2017", show=False, save=True)

# h) Add carbon emission constraints
network.build_network(storage=True, transmission=True, external=True, gas=True, co2_limit=True, limit=28_000_000 * 0.01)

network.optimize_network()

co2_price = network.network.global_constraints.mu
print("--------------------------------------------------------")
print("CO2 Price: ")
print(co2_price)
print("--------------------------------------------------------")
