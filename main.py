import pandas as pd
from data_loader import load_data
from plotter import *
from network import Network
from helper import *

### SECTION CONTROLS ###
RUN_A_C = False # with and without storage single node 
RUN_D = False # + transmission 
RUN_E = False # imbalances
RUN_F = False # CO2 limit analysis
RUN_G = False # H2 network
RUN_H = True # CO2 constraint
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

    dispatch.index = dispatch.index.tz_localize(None)
    load.index = load.index.tz_localize(None)
    
    imbalances = calculate_imbalances(dispatch, load)

    # first hour only (as a Series)
    first_hour = imbalances.iloc[0]

    # convert to DataFrame with same structure as before
    imbalance_df = pd.DataFrame(first_hour).T
    imbalance_df.index = [dispatch.index[0]]

    print("--------------------------------------------------------")
    print("Imbalances in each node for the first hour:")
    print(imbalance_df)

    # power flows (unchanged)
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

    plot_h2_capacity_mix_by_country(
        network.network,
        f"H2 Installed Capacity Split by Country 2017 ({scenario_label})",
        show=False,
        save=True,
    )

    plot_total_transmission_comparison(dispatch, title=f"Total Transported Energy in 2017 ({scenario_label})", show=False, save=True)

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
    run_co2_limit_plots = False
    run_co2_limit_sensitivity = True

    co2_1990_ee = 28_300_000 # tons of CO2 (electricity and heating sector) in 1990 for Estonia
    co2_1990_fi = 19_900_000 # tons of CO2 (electricity and heating sector) in 1990 for Finland
    co2_1990_se = 9_800_000 # tons of CO2 (electricity and heating sector) in 1990 for Sweden
    co2_1990_lv = 9_850_000 # tons of CO2 (electricity and heating sector) in 1990 for Latvia
    co2_1990_total = co2_1990_ee + co2_1990_fi + co2_1990_se + co2_1990_lv
    
    
    def co2_reduction_plots(dispatch, capacities, network, reduction_target):
        scenario_label = f"with storage, transmission, H2, and CO2 constraint ({int(reduction_target) * 100}% reduction)"
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
        

        co2_price = network.network.global_constraints.mu.values[0]
        print("--------------------------------------------------------")
        print("CO2 Price: ")
        print(co2_price)
        print("--------------------------------------------------------")

        return
    
    if run_co2_limit_sensitivity:
        sens_co2_limits = [0.55, 0.6, 0.65, 0.7, 0.725, 0.75, 0.8, 0.85, 0.9, 0.95, 0.99] # reduction targets from 1990 levels (e.g., 0.7 means 70% reduction, i.e., 30% of 1990 levels)
        sens_co2_results = []
        for reduction_target in sens_co2_limits:
            # Recalculate co2_limit based on the current reduction_target
            co2_limit = (1 - reduction_target) * co2_1990_total
            network = Network(load, wind_cf, solar_cf, hours=hours)
            network.build_network(storage=True, transmission=True, external=True, h2=True, co2_limit=True, limit=co2_limit)

            network.optimize_network()
            dispatch, capacities = network.save_results()

            co2_price = -network.network.global_constraints.mu.iloc[0]
            sens_co2_results.append(co2_price)
            
            print(f"Reduction target: {int(reduction_target * 100)}%, CO2 limit: {co2_limit:.0f} tons, CO2 price: {co2_price:.2f} €/ton")
        
        plot_co2_price_sensitivity(sens_co2_limits, sens_co2_results, f"Sensitivity of CO2 Price to Emission Reduction Targets", show=False, save=True)

    else:
        reduction_target = 0.7 # 70% reduction from 1990 levels
        co2_limit = (1 - reduction_target) * co2_1990_total
        print(f"Applying CO2 limit of {co2_limit:.0f} tons, which is {int((1 - reduction_target) * 100)}% of 1990 levels for the entire region.")
        
        network = Network(load, wind_cf, solar_cf, hours=hours)
        network.build_network(storage=True, transmission=True, external=True, h2=True, co2_limit=True, limit=co2_limit)

        network.optimize_network()
        dispatch, capacities = network.save_results()
        co2_reduction_plots(dispatch, capacities, network, reduction_target)

    # sens_co2_limits = [0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.99] # reduction targets from 1990 levels (e.g., 0.7 means 70% reduction, i.e., 30% of 1990 levels)

    # sens_co2_results = [0.16, 10.70, 35.53, 62.68, 97.58, 144.11, 175.87, 247.43, 446.79, 1694.32] # dummy results for testing the plotting function

    # plot_co2_price_sensitivity(sens_co2_limits, sens_co2_results, f"Sensitivity of CO2 Price to Emission Reduction Targets", show=False, save=True)

    

    


if RUN_I:
    
    # i) Add heat sector
    scenario_label = "with storage, transmission, H2, CO2 constraint, and heat"
    
    network = Network(load,wind_cf, solar_cf,hours=hours, heat_demand=heat_demand, cop=cop)
    network.build_network(storage=True, transmission=True, external=True, h2=True, co2_limit=True, limit=68_750_000 * 0.1, heat=True)
    network.optimize_network()
    dispatch, capacities = network.save_results()
    
    plot_capacity_mix_by_country_heat(capacities, f"Optimal Installed Capacity Mix by Country 2017 ({scenario_label})", show=False, save=True)
    
    plot_heat_dispatch(time_index=january_week,df=dispatch[january_week_mask],heat_demand=heat_demand["EE"][january_week_mask],node="Estonia",title=f"Estonia Heat Dispatch ({scenario_label})",show=False,save=True)
    
    h2_pipeline_capacities = network.network.links.loc[
    network.network.links.index.str.contains("H2 Pipeline"),
    "p_nom_opt",
        ].sum()

    print("--------------------------------------------------------")
    print(f"Total H2 pipeline capacity installed: {h2_pipeline_capacities:.1f} MW")
    print("--------------------------------------------------------")
