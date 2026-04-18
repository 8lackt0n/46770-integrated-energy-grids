import pandas as pd
from data_loader import load_data
from helper import annuity, annualize
import pypsa
from plotter import *
#---------------------------------------------------
### PYPSA NETWORK ###
class Network():
    
    def __init__(self, load, wind_cf, solar_cf, hours):
        self.network = pypsa.Network()
        self.load = load
        self.wind_cf = wind_cf
        self.solar_cf = solar_cf
        self.hours = hours
    
    def build_network(self, storage=False, transmission=False, external=False, gas=False, co2_limit=False, limit=None):

        # PyPSA requires timezone-naive snapshots.
        snapshots = pd.DatetimeIndex(self.hours)
        if snapshots.tz is not None:
            snapshots = snapshots.tz_localize(None)
        self.network.set_snapshots(snapshots)
        # Add a bus
        self.network.add("Bus", "Estonia", v_nom=400)

        # Add a load
        self.network.add("Load", 
                    "Estonia_Load",
                    bus="Estonia", 
                    p_set=self.load['EE'].values)
        
        self.network.loads_t.p_set

        # Add network carriers
        self.network.add("Carrier", "Wind", co2_emissions=0)
        self.network.add("Carrier", "Solar", co2_emissions=0)
        self.network.add("Carrier", "Gas", co2_emissions=0.19) # tonnes co2 / MWh_th
        self.network.add("Carrier", "Coal", co2_emissions=1.0) # tonnes co2 / MWh_th
        self.network.add("Carrier", "Nuclear", co2_emissions=0)
        self.network.add("Carrier", "Hydro", co2_emissions=0)

        # Add network generators
        
        # Onshore Wind
        # https://www.sciencedirect.com/science/article/pii/S0196890419309835?via%3Dihub
        capital_cost_wind = annuity(30,0.07)*910_000*(1+0.033) # in €/MW
        self.network.add("Generator", 
                    "Wind Generator Estonia", 
                    p_nom_extendable=True,
                    bus="Estonia", 
                    carrier="Wind", 
                    capital_cost = capital_cost_wind,
                    p_max_pu=self.wind_cf['EE'].values)
        
        # PV
        # https://www.sciencedirect.com/science/article/pii/S0196890419309835?via%3Dihub
        capital_cost_solar = annuity(25,0.07)*425_000*(1+0.03) # in €/MW
        self.network.add("Generator", 
                    "Solar Generator Estonia", 
                    p_nom_extendable=True,
                    bus="Estonia", 
                    carrier="Solar", 
                    capital_cost = capital_cost_solar,
                    p_max_pu=self.solar_cf['EE'].values)
        
        # OCGT Power Plant
        # https://www.sciencedirect.com/science/article/pii/S0196890419309835?via%3Dihub
        capital_cost_OCGT = annuity(25,0.07)*560_000*(1+0.033) # in €/MW
        fuel_cost = 21.6 # in €/MWh_th
        efficiency_gas = 0.39 # MWh_elec/MWh_th
        marginal_cost_OCGT = fuel_cost/efficiency_gas # in €/MWh_el
        self.network.add("Generator",
                    "OCGT Estonia",
                    bus="Estonia",
                    p_nom_extendable=True,
                    carrier="Gas",
                    efficiency=efficiency_gas,
                    capital_cost = capital_cost_OCGT,
                    marginal_cost = marginal_cost_OCGT)
        
        # Ignite Fired Power Plant
        # https://www.econstor.eu/handle/10419/80348
        over_night_cost_IFPP = annualize(1_400_000, 2012, 2017) # in €/MW
        capital_cost_coal = annuity(25,0.07)*over_night_cost_IFPP*(1+0.033) # in €/MW
        fuel_cost_coal = 12.95 # in €/MWh_th, source: https://ourworldindata.org/grapher/coal-prices
        efficiency_coal = 0.35 # MWh_elec/MWh_th
        marginal_cost_coal = fuel_cost_coal/efficiency_coal # in €/MWh_el
        
        self.network.add("Generator",
                    "Coal Estonia",
                    bus="Estonia",
                    p_nom_extendable=True,
                    carrier="Coal",
                    efficiency=efficiency_coal,
                    capital_cost = capital_cost_coal,
                    marginal_cost = marginal_cost_coal)
        
        if storage:
            self.add_storage()
        if transmission:
            self.add_transmission()
        if external:
            self.add_external()
        if gas:
            self.add_gas_network()
        if co2_limit:
            self.add_co2_limit(limit)

        
        self.network.sanitize()
        
    def add_storage(self):

        # https://www.sciencedirect.com/science/article/pii/S0378775312014759?via%3Dihub
        over_night_cost_battery = annualize(409_000, 2008, 2017) # in €/MW
        capital_cost = annuity(20, 0.07) * over_night_cost_battery * (1 + 0.033) # in €/MW
        marginal_cost = 0.0

        efficiency_store = 0.9
        efficiency_dispatch = 0.9

        max_hours = 8  # energy capacity = power * hours

        self.network.add("StorageUnit",
                        "Battery Storage Estonia",
                        bus="Estonia",
                        p_nom_extendable=True,
                        capital_cost=capital_cost,
                        marginal_cost=marginal_cost,
                        efficiency_store=efficiency_store,
                        efficiency_dispatch=efficiency_dispatch,
                        max_hours=max_hours,
                        cyclic_state_of_charge=True)
        
    def add_transmission(self):

    
        # Fenno-Skan 1+2 (Sweden-Finland ) (500+800 = 1200 MW) 400 kV (1989 and 2011)
        # Estlink 1+2 (Estonia-Finland) (350+650 = 1000 MW) 330 kV (Estonia) and 400 kV (finland) (2006 and 2014)
        # Theortical Estonia-Sweden (700? MW) Would likely be similar, 330 kV Estonia and 400 kV Sweden 
        # Estonia Latvia interconnection (1400 MW or 800 MW, depending on how new) 330 kV (1970ish, 1970ish, 2020 (1 and 2 were reconstructed 2023/2024))
        for b in ["Estonia", "Finland", "Sweden", "Latvia"]:
            if b not in self.network.buses.index:
                self.network.add("Bus", b, v_nom=400)

        cap_fin_swe = 1200.0   # Fenno-Skan 1+2 (500 + 800)
        cap_est_fin = 1000.0   # Estlink 1+2 (350 + 650)
        cap_est_swe = 700.0    # Theoretical Estonia-Sweden
        cap_est_lat = 1400.0   # Estonia-Latvia interconnection (using latest estimate)

        x = 0.1                 # unitary reactance
        extendable = False      # fixed capacities

        self.network.add("Line",
                        "FIN-SWE",
                        bus0="Finland",
                        bus1="Sweden",
                        s_nom=cap_fin_swe,
                        s_nom_extendable=extendable,
                        x=x)

        self.network.add("Line",
                        "EST-FIN",
                        bus0="Estonia",
                        bus1="Finland",
                        s_nom=cap_est_fin,
                        s_nom_extendable=extendable,
                        x=x)

        self.network.add("Line",
                        "EST-SWE",
                        bus0="Estonia",
                        bus1="Sweden",
                        s_nom=cap_est_swe,
                        s_nom_extendable=extendable,
                        x=x)

        self.network.add("Line",
                        "EST-LAT",
                        bus0="Estonia",
                        bus1="Latvia",
                        s_nom=cap_est_lat,
                        s_nom_extendable=extendable,
                        x=x)

    def add_external(self):
        
        # Add bus for each country
        self.network.add("Bus", "Finland")
        self.network.add("Bus", "Sweden")
        self.network.add("Bus", "Latvia")

        # Add loads for each country
        self.network.add("Load", 
                    "Finland_Load",
                    bus="Finland", 
                    p_set=self.load['FI'].values)
        self.network.loads_t.p_set
        
        self.network.add("Load", 
                    "Sweden_Load",
                    bus="Sweden", 
                    p_set=self.load['SE'].values)
        self.network.loads_t.p_set
        
        self.network.add("Load", 
                    "Latvia_Load",
                    bus="Latvia",
                    p_set=self.load['LV'].values)
        self.network.loads_t.p_set
        
        
        # Add generators in neigbouring coutries
        
        # https://www.econstor.eu/handle/10419/80348

        over_night_cost_nuclear = annualize(4_000_000, 2010, 2017) # in €/MW
        capital_cost_nuclear = annuity(25,0.07)*over_night_cost_nuclear*(1+0.033) # in €/MW
        fuel_cost = 12 # in €/MWh_th
        efficiency = 0.33 # MWh_elec/MWh_th
        marginal_cost_Nuclear = fuel_cost/efficiency # in €/MWh_el
        self.network.add(
            "Generator",
            "Nuclear Finland",
            bus="Finland",
            carrier="Nuclear",
            p_nom_extendable=True,
            capital_cost = capital_cost_nuclear,
            marginal_cost = marginal_cost_Nuclear
        )
        
        # Onshore Wind
        # https://www.sciencedirect.com/science/article/pii/S0196890419309835?via%3Dihub
        capital_cost_wind = annuity(30,0.07)*910_000*(1+0.033) # in €/MW
        self.network.add("Generator", 
                    "Wind Generator Finland", 
                    p_nom_extendable=True,
                    bus="Finland", 
                    carrier="Wind", 
                    capital_cost = capital_cost_wind,
                    p_max_pu=self.wind_cf['FI'].values)
        
        
        
        # https://www.sciencedirect.com/science/article/pii/S0378775312014759?via%3Dihub
        capital_cost_hydro = annuity(80,0.07)*2_000_000*(1+0.033) # in €/MW
        marginal_cost_hydro = 0
        self.network.add(
            "Generator",
            "Hydro Sweden",
            bus="Sweden",
            carrier="Hydro",
            p_nom_extendable=True,
            capital_cost=capital_cost_hydro,
            marginal_cost=marginal_cost_hydro
        )
        
        # https://www.sciencedirect.com/science/article/pii/S0196890419309835?via%3Dihub
        capital_cost_wind = annuity(30,0.07)*910_000*(1+0.033) # in €/MW
        self.network.add("Generator", 
                    "Wind Generator Sweden", 
                    p_nom_extendable=True,
                    bus="Sweden", 
                    carrier="Wind", 
                    capital_cost = capital_cost_wind,
                    p_max_pu=self.wind_cf['SE'].values)
        
        
        # Ignite Fired Power Plant
        # https://www.econstor.eu/handle/10419/80348
        over_night_cost_IFPP = annualize(1_400_000, 2012, 2017) # in €/MW
        capital_cost_coal = annuity(25,0.07)*over_night_cost_IFPP*(1+0.033) # in €/MW
        fuel_cost_coal = 12.95 # in €/MWh_th, source: https://ourworldindata.org/grapher/coal-prices
        efficiency_coal = 0.35 # MWh_elec/MWh_th
        marginal_cost_coal = fuel_cost_coal/efficiency_coal # in €/MWh_el
        
        self.network.add("Generator",
                    "Coal Latvia",
                    bus="Latvia",
                    p_nom_extendable=True,
                    carrier="Coal",
                    efficiency = efficiency_coal,
                    capital_cost = capital_cost_coal,
                    marginal_cost = marginal_cost_coal)
        
        # https://www.sciencedirect.com/science/article/pii/S0196890419309835?via%3Dihub
        capital_cost_wind = annuity(30,0.07)*910_000*(1+0.033) # in €/MW
        self.network.add("Generator", 
                    "Wind Generator Latvia", 
                    p_nom_extendable=True,
                    bus="Latvia", 
                    carrier="Wind", 
                    capital_cost = capital_cost_wind,
                    p_max_pu=self.wind_cf['LV'].values)
    
    def add_co2_limit(self, limit):
        self.network.add(
            "GlobalConstraint",
            "co2_limit",
            type="primary_energy",
            carrier_attribute="co2_emissions",
            sense="<=",
            constant=limit  # total CO2 limit (e.g. in tonnes)
        )
    
    def add_gas_network(self):
        
        gas_price = 21.6  # €/MWh_th

        # Add gas buses for each country
        for country in ["Estonia", "Latvia", "Sweden", "Finland"]:
            # Add busses
            if f"{country} gas" not in self.network.buses.index:
                self.network.add(
                    "Bus", 
                    f"{country} gas",
                    carrier="Gas",
                    v_nom=0,
        )
            
            
        # Remove the OCGT generator from the electricity network to avoid duplication
        if "OCGT Estonia" in self.network.generators.index:
            self.network.remove("Generator", "OCGT Estonia")
        
        # Add gas supply from Lativa
        self.network.add(
            "Generator",
            "Gas Supply Latvia",
            bus="Latvia gas",
            carrier="Gas",
            p_nom_extendable=True,
            marginal_cost=gas_price
        )
        
        # Add gas generators
        
        # https://www.sciencedirect.com/science/article/pii/S0196890419309835?via%3Dihub
        capital_cost_OCGT = annuity(25,0.07)*560_000*(1+0.033) # in €/MW
        efficiency_gas = 0.39 # MWh_elec/MWh_th
        marginal_cost_OCGT = gas_price/efficiency_gas # in €/MWh_el
        
        self.network.add(
            "Link",
            "OCGT Estonia",
            bus0="Estonia gas",
            bus1="Estonia",
            carrier="Gas",
            p_nom_extendable=True,
            efficiency=efficiency_gas,
            capital_cost = capital_cost_OCGT,
            marginal_cost = marginal_cost_OCGT
        )
        
        self.network.add(
            "Link",
            "OCGT Sweden",
            bus0="Sweden gas",
            bus1="Sweden",
            carrier="Gas",
            p_nom_extendable=True,
            efficiency=efficiency_gas,
            capital_cost = capital_cost_OCGT,
            marginal_cost = marginal_cost_OCGT
        )
        
        self.network.add(
            "Link",
            "OCGT Finland",
            bus0="Finland gas",
            bus1="Finland",
            carrier="Gas",
            p_nom_extendable=True,
            efficiency=efficiency_gas,
            capital_cost = capital_cost_OCGT,
            marginal_cost = marginal_cost_OCGT
        )
        
        # Add gas pipelines between countries        
        
        pipeline_efficiency = 1     # linear/lossless first approximation

        self.network.add(
                        "Link",
                        "FIN-SWE Gas Pipeline",
                        bus0="Finland gas",
                        bus1="Sweden gas",
                        carrier="Gas",
                        p_nom_extendable=True,
                        p_min_pu=-1,    # allow both directions
                        efficiency=pipeline_efficiency,
                        marginal_cost = 0)

        self.network.add(
                        "Link",
                        "EST-FIN Gas Pipeline",
                        bus0="Estonia gas",
                        bus1="Finland gas",
                        carrier="Gas",
                        p_nom_extendable=True,
                        p_min_pu=-1,    # allow both directions
                        efficiency=pipeline_efficiency,
                        marginal_cost = 0)

        self.network.add(
                        "Link",
                        "EST-SWE Gas Pipeline",
                        bus0="Estonia gas",
                        bus1="Sweden gas",
                        carrier="Gas",
                        p_nom_extendable=True,
                        p_min_pu=-1,    # allow both directions
                        efficiency=pipeline_efficiency,
                        marginal_cost = 0)  

        self.network.add(
                        "Link",
                        "EST-LAT Gas Pipeline",
                        bus0="Estonia gas",
                        bus1="Latvia gas",
                        carrier="Gas",
                        p_nom_extendable=True,
                        p_min_pu=-1,    # allow both directions
                        efficiency=pipeline_efficiency,
                        marginal_cost = 0)
          
    def optimize_network(self):
        self.network.optimize(
            solver_name="gurobi",
            solver_options={"OutputFlag": 0},
            include_objective_constant=True 
        )

    def display_results(self):
        
        dispatch = pd.DataFrame(index=self.network.snapshots)
        capacities_dict = {}

        estonia_gens = self.network.generators.index[
            self.network.generators.bus == "Estonia"
            ]

        if len(estonia_gens) > 0:
            gen_dispatch = self.network.generators_t.p[estonia_gens].copy()
            dispatch = pd.concat([dispatch, gen_dispatch], axis=1)

        
        for country in ["Estonia", "Finland", "Sweden", "Latvia"]:
            country_links = self.network.links.index[
            self.network.links.bus1 == country
            ]

            for link_name in country_links:
                # Electricity output at bus1 is usually -p1
                dispatch[link_name] = -self.network.links_t.p1[link_name]

                capacities_dict[link_name] = self.network.links.at[link_name, "p_nom_opt"]

        storage_data = None
        battery_capacity = None

        if not self.network.storage_units.empty:
            estonia_storage = self.network.storage_units.index[
                self.network.storage_units.bus == "Estonia"
            ]

            if len(estonia_storage) > 0:
                storage_p = self.network.storage_units_t.p[estonia_storage].copy()
                storage_soc = self.network.storage_units_t.state_of_charge[estonia_storage].copy()

                storage_name = estonia_storage[0]
                storage_power = float(self.network.storage_units.at[storage_name, "p_nom_opt"])
                storage_hours = float(self.network.storage_units.at[storage_name, "max_hours"])
                battery_capacity = storage_power * storage_hours

                dispatch["Battery Storage Discharge"] = storage_p[storage_name].clip(lower=0)
                dispatch["Battery Storage Charge"] = -storage_p[storage_name].clip(upper=0)
                dispatch["Battery Storage SoC"] = storage_soc[storage_name]

                capacities_dict["Battery Storage"] = storage_power

                storage_data = pd.DataFrame(
                    {
                        "Battery Storage Discharge": dispatch["Battery Storage Discharge"],
                        "Battery Storage Charge": dispatch["Battery Storage Charge"],
                        "Battery Storage SoC": dispatch["Battery Storage SoC"],
                    },
                    index=dispatch.index,
                )

        
        # add capacites from external generators and links if they exist
        capacities = pd.Series(capacities_dict)
        all_gen_capacities = self.network.generators.loc[:, "p_nom_opt"].to_dict()
        capacities = pd.concat([capacities, pd.Series(all_gen_capacities)], ignore_index=False)
        
        

        dispatch_all = self.network.generators_t.p.copy()

        return dispatch, capacities, storage_data, battery_capacity, dispatch_all
     
    def save_results(self):
        
        print("Saving results...")
        
        capacacities = pd.DataFrame()
        
        dispatch = pd.DataFrame(index=self.network.snapshots)
        
        
        if not self.network.generators.empty:
            gen_capacities = self.network.generators.p_nom_opt
            capacacities = pd.concat([capacacities, gen_capacities], ignore_index=False)
            
            gen_dispatch = self.network.generators_t.p.copy()
            dispatch = pd.concat([dispatch, gen_dispatch], axis=1)
            
        if not self.network.links.empty:
            link_capacities = self.network.links.p_nom_opt
            capacacities = pd.concat([capacacities, link_capacities], ignore_index=False)
            
            link_dispatch = -self.network.links_t.p1.copy() 
            dispatch = pd.concat([dispatch, link_dispatch], axis=1)
        
        if not self.network.storage_units.empty:
            storage_capacities = self.network.storage_units_t.state_of_charge.max().copy()
            storage_capacities = storage_capacities.rename("p_nom_opt")
            capacacities = pd.concat([capacacities, storage_capacities], ignore_index=False)

            charge = self.network.storage_units_t.p_store.copy()
            discharge = self.network.storage_units_t.p_dispatch.copy()
            soc = self.network.storage_units_t.state_of_charge.copy()
            
            dispatch = pd.concat(
                [dispatch, charge.rename(columns={"Battery Storage Estonia": "Battery Charge Estonia"}), 
                 discharge.rename(columns={"Battery Storage Estonia": "Battery Discharge Estonia"}), 
                 soc.rename(columns={"Battery Storage Estonia": "Battery SoC Estonia"})], axis=1)

            
        if not self.network.lines.empty:
            line_capacities = self.network.lines.s_nom_opt
            capacacities = pd.concat([capacacities, line_capacities], ignore_index=False)
            
            line_flows = self.network.lines_t.p0.copy()
            dispatch = pd.concat([dispatch, line_flows], axis=1)    
            
        
        return dispatch, capacacities

if __name__ == "__main__":
    
    ### LOADING DATA ###

    print("Loading data...")
    load, wind_cf, solar_cf = load_data(year=2017)

    print(f"Load series length: {len(load)}")
    print(f"Wind CF series length: {len(wind_cf)}")
    print(f"Solar CF series length: {len(solar_cf)}")
    
    hours = pd.date_range('2017-01-01 00:00','2017-12-31 23:00',freq='h')
    
    january_week_mask = (hours >= '2017-01-01') & (hours < '2017-01-08')
    january_week = hours[january_week_mask]
    
    ### ANALYSIS ###
    # f) CO2 limit analysis
    # https://kliimaministeerium.ee/sites/default/files/documents/2024-04/Energy%20summary_2024.pdf?
    # base_co2 = 28_000_000
    
    # scenario_results = []
    
    # co2_limits = [base_co2, 0.2 * base_co2, 0.1 * base_co2, 0.05 * base_co2, 0] # in tons of CO2
    
    # for co2_limit in co2_limits:
    #     network = Network(load, wind_cf, solar_cf, hours=hours)
        
    #     network.build_network(storage=True)
        
    #     network.add_co2_limit(co2_limit)
        
    #     network.optimize_network()
        
    #     _, capacities = network.save_results()
        
    #     scenario_results.append(
    #             {
    #                 "co2_limit": co2_limit,
    #                 "capacities": capacities,
    #             }
    #         )

    # plot_capacities_vs_co2_limits(scenario_results, f"Installed Capacities under Different CO2 Emission Limits Estonia, 2017", show=False, save=True)
    
    # g) Gas transmission analysis
    # network = Network(load, wind_cf, solar_cf, hours=hours)
    # network.build_network(storage=True, transmission=True, external=True, gas=True)
    
    # network.optimize_network()
    # dispatch, capacities = network.save_results()
    
    # plot_total_transmission_comparison(dispatch, title="Total Transported Energy in 2017", show=True, save=False)
    
    # h) CO2 price analysis
    # network = Network(load, wind_cf, solar_cf, hours=hours)
    # network.build_network(storage=True, transmission=True, external=True, gas=True, co2_limit=True, limit=0.05*28_000_000)
    
    # network.optimize_network()
    # dispatch, capacities = network.save_results()
    # co2_price = network.network.global_constraints.mu
    # print(co2_price)
    
    
    