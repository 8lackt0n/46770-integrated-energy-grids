import pandas as pd
from data_loader import load_data
from plotter import *
from network import Network
from helper import *

### SECTION CONTROLS ###
RUN_A_C = True # with and without storage single node 
RUN_D = False # + transmission 
RUN_E = False # imbalances
RUN_F = False # CO2 limit analysis
RUN_G = False # H2 network
RUN_H = False # CO2 constraint
RUN_I = False # heat sector

### LOADING DATA ###

print("Loading data...")
load, wind_cf, solar_cf, heat_demand, cop = load_data(year=2017)

print(f"Load series length: {len(load)}")
print(f"Wind CF series length: {len(wind_cf)}")
print(f"Solar CF series length: {len(solar_cf)}")
print(f"Heat Demand series length: {len(heat_demand)}")
print(f"COP series length: {len(cop)}")
hours = pd.date_range('2017-01-01 00:00','2017-12-31 23:00',freq='h')

january_week_mask = (hours >= '2017-01-01') & (hours < '2017-01-08')
january_week = hours[january_week_mask]

july_week_mask = (hours >= '2017-07-01') & (hours < '2017-07-08')
july_week = hours[july_week_mask]

load_est = load["EE"]


def print_h2_capacity_summary(network):
    h2_links = network.network.links
    h2_stores = network.network.stores

    electrolyzers = h2_links.loc[h2_links.index.str.contains("Electrolyzer", regex=True), "p_nom_opt"].sum()
    turbines = h2_links.loc[h2_links.index.str.contains("H2 Turbine", regex=True), "p_nom_opt"].sum()
    pipelines = h2_links.loc[h2_links.index.str.contains("H2 Pipeline", regex=True), "p_nom_opt"].sum()
    storage_energy = h2_stores.loc[h2_stores.index.str.contains("H2 Storage", regex=True), "e_nom_opt"].sum()

    print("--------------------------------------------------------")
    print(f"H2 electrolyzers installed: {electrolyzers:.1f} MW")
    print(f"H2 turbines installed: {turbines:.1f} MW")
    print(f"H2 pipelines installed: {pipelines:.1f} MW")
    print(f"H2 storage installed: {storage_energy:.1f} MWh")
    print("--------------------------------------------------------")

### ANALYSIS ###

if RUN_A_C:
    # a) and c) (see interannual for b))
    scenarios = [(False, "without storage"), (True, "with storage")]

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
                "soc_axis_max": capacities.get('Battery Storage Estonia', 0) if storage_enabled else 0,
            }
        )

    shared_power_axis_max = max(
        compute_shared_power_axis_max(result["dispatch"], load["EE"])
        for result in scenario_results
    )

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
            soc_axis_max=soc_axis_max,
        )

        plot_dispatch(
            july_week,
            dispatch[july_week_mask],
            load_est[july_week_mask],
            f"Optimal Hourly Dispatch for One Week in July 2017 ({scenario_label})",
            power_axis_max=shared_power_axis_max,
            soc_axis_max=soc_axis_max,
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

if RUN_D:
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
    plot_transmission_network(dispatch, load, f"Transmission Network Flows 2017 ({scenario_label})", show=False, save=True)
    plot_country_balance(dispatch, load, f"Country Energy Balance 2017 ({scenario_label})", show=False, save=True)
    plot_duration_curve(dispatch, f"Duration Curve for 2017 ({scenario_label})")

    electric_columns = [
        "FIN-SWE",
        "EST-FIN",
        "EST-SWE",
        "EST-LAT",
    ]
    electric_total_d = dispatch[[col for col in electric_columns if col in dispatch.columns]].abs().sum().sum() / 1000

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

if RUN_E:
    # e)
    if not RUN_D:
        raise RuntimeError("Section e requires section d to be enabled.")

    # calculate imbalances in each node for the first hour
    # Finland
    generation_finland = dispatch['Wind Generator Finland'].iloc[0] + dispatch['Nuclear Finland'].iloc[0]+dispatch['OCGT Finland'].iloc[0]
    imbalance_finland = generation_finland - load['FI'].iloc[0]
    # Sweden (SE2)
    generation_sweden = dispatch['Wind Generator Sweden'].iloc[0] + dispatch['Hydro Sweden'].iloc[0]+dispatch['OCGT Sweden'].iloc[0]
    imbalance_sweden = generation_sweden - load['SE'].iloc[0]
    # Latvia
    generation_latvia = dispatch['Wind Generator Latvia'].iloc[0] + dispatch['Coal Latvia'].iloc[0]+dispatch['OCGT Latvia'].iloc[0]
    imbalance_latvia = generation_latvia - load['LV'].iloc[0]

    generation_estonia = dispatch['Wind Generator Estonia'].iloc[0] + dispatch['Coal Estonia'].iloc[0] + dispatch['Solar Generator Estonia'].iloc[0] + dispatch['OCGT Estonia'].iloc[0] + dispatch['Battery Discharge Estonia'].iloc[0]
    imbalance_estonia = generation_estonia - (load['EE'].iloc[0] + dispatch['Battery Charge Estonia'].iloc[0])

    # create dataframe for imbalances
    imbalance_df = pd.DataFrame({
        "Finland": imbalance_finland,
        "Sweden": imbalance_sweden,
        "Latvia": imbalance_latvia,
        "Estonia": imbalance_estonia,
    }, index=[dispatch.index[0]])
    print("--------------------------------------------------------")

    print("Imbalances in each node for the first hour:")
    print(imbalance_df)

    # print power flows in each line for the first hour
    print("Power flows in each line for the first hour:")
    print(network.network.lines_t.p0.loc[network.network.snapshots[0]])
    print("--------------------------------------------------------")

if RUN_F:
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

    plot_capacities_vs_co2_limits(scenario_results, base_co2, f"Installed Capacities under Different CO2 Emission Limits Estonia, 2017", show=False, save=True)
if RUN_G:
    # g) Add H2 transmission network

    network = Network(load,wind_cf, solar_cf, hours=hours)

    network.build_network(storage=True, transmission=True, external=True, h2=True)

    network.optimize_network()

    dispatch, capacities = network.save_results()

    soc_max = capacities.get('Battery Storage Estonia', 0)

    scenario_label = "with storage, transmission, and H2 network"

    shared_power_axis_max = compute_shared_power_axis_max(dispatch, load_est)

    # --- PLOTS ---
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

    plot_transmission_network(dispatch, load, f"Transmission Network Flows 2017 ({scenario_label})", show=False, save=True)
    plot_country_balance(dispatch, load, f"Country Energy Balance 2017 ({scenario_label})", show=False, save=True)
    plot_duration_curve(dispatch, f"Duration Curve for 2017 ({scenario_label})")

    plot_capacity_mix_by_country(
        capacities,
        f"Optimal Installed Capacity Mix by Country 2017 ({scenario_label})",
        show=False,
        save=True,
    )

    plot_h2_capacity_mix_by_country(
        network.network,
        f"H2 Installed Capacity Split by Country 2017 ({scenario_label})",
        show=False,
        save=True,
    )

    plot_total_transmission_comparison(dispatch, title="Total Transported Energy in 2017", show=False, save=True)

    plot_h2_transmission_network(dispatch, title="H2 Transmission Network 2017", show=False, save=True)

    # plot_h2_storage_operation(
    #     january_week,
    #     dispatch[january_week_mask],
    #     title=f"H2 Storage Operation for One Week in January 2017 ({scenario_label})",
    #     show=False,
    #     save=True,
    # )

    # plot_h2_storage_operation(
    #     july_week,
    #     dispatch[july_week_mask],
    #     title=f"H2 Storage Operation for One Week in July 2017 ({scenario_label})",
    #     show=False,
    #     save=True,
    # )

    print_h2_capacity_summary(network)


if RUN_H:
    # h) Add carbon emission constraints

    network = Network(load,wind_cf, solar_cf, hours=hours)
    network.build_network(storage=True, transmission=True, external=True, h2=True, co2_limit=True, limit=28_000_000 * 0.1)

    network.optimize_network()

    dispatch, capacities = network.save_results()

    scenario_label = "with storage, transmission, H2, and CO2 constraint"
    soc_max = capacities.get('Battery Storage Estonia', 0)
    shared_power_axis_max = compute_shared_power_axis_max(dispatch, load_est)

    plot_dispatch(
        january_week,
        dispatch[january_week_mask],
        load_est[january_week_mask],
        f"Optimal Hourly Dispatch for One Week in January 2017 ({scenario_label})",
        power_axis_max=shared_power_axis_max,
        soc_axis_max=soc_max,
    )

    plot_dispatch(
        july_week,
        dispatch[july_week_mask],
        load_est[july_week_mask],
        f"Optimal Hourly Dispatch for One Week in July 2017 ({scenario_label})",
        power_axis_max=shared_power_axis_max,
        soc_axis_max=soc_max,
    )

    plot_capacity_mix_by_country(capacities, f"Optimal Installed Capacity Mix by Country 2017 ({scenario_label})", show=False, save=True)

    plot_transmission_network(dispatch, load, f"Transmission Network Flows 2017 ({scenario_label})", show=False, save=True)
    plot_country_balance(dispatch, load, f"Country Energy Balance 2017 ({scenario_label})", show=False, save=True)
    plot_duration_curve(dispatch, f"Duration Curve for 2017 ({scenario_label})")

    plot_h2_capacity_mix_by_country(
        network.network,
        f"H2 Installed Capacity Split by Country 2017 ({scenario_label})",
        show=False,
        save=True,
    )

    plot_total_transmission_comparison(dispatch, title="Total Transported Energy in 2017 (CO2_constraint)", show=False, save=True)

    plot_h2_transmission_network(dispatch, title="H2 Transmission Network 2017 (CO2_constraint)", show=False, save=True)

    plot_h2_storage_operation(
        january_week,
        dispatch[january_week_mask],
        title=f"H2 Storage Operation for One Week in January 2017 ({scenario_label})",
        show=False,
        save=True,
    )

    plot_h2_storage_operation(
        july_week,
        dispatch[july_week_mask],
        title=f"H2 Storage Operation for One Week in July 2017 ({scenario_label})",
        show=False,
        save=True,
    )

    print_h2_capacity_summary(network)
    

    co2_price = network.network.global_constraints.mu
    print("--------------------------------------------------------")
    print("CO2 Price: ")
    print(co2_price)
    print("--------------------------------------------------------")

if RUN_I:
    
    # i) Add heat sector
    network = Network(load,wind_cf, solar_cf,hours=hours, heat_demand=heat_demand, cop=cop)
    network.build_network(storage=True, transmission=True, external=True, h2=True, co2_limit=True, limit=28_000_000 * 0.2, heat=True)
    network.optimize_network()
    dispatch, capacities = network.save_results()
    plot_capacity_mix_by_country(capacities, f"Optimal Installed Capacity Mix by Country 2017 (with Storage, Transmission, H2, and Heat)", show=False, save=True)