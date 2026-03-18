import pandas as pd
from data_loader import load_data
from helper import annuity
import pypsa
import gurobipy
import matplotlib.pyplot as plt
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
    
    def build_network(self):
        

        # Set snapshot times
        self.network.set_snapshots(self.hours.values)
        # Add a bus
        self.network.add("Bus", "Electricity Bus")

        # Add a load
        self.network.add("Load", 
                    "Electricity Load",
                    bus="Electricity Bus", 
                    p_set=self.load.values)
        self.network.loads_t.p_set

        # Add network carriers
        self.network.add("Carrier", "Wind")
        self.network.add("Carrier", "Solar")
        self.network.add("Carrier", "Gas", co2_emissions=0.19)
        self.network.add("Carrier", "Coal", co2_emissions=1.0)

        # Add network generators
        capital_cost_wind = annuity(30,0.07)*910000*(1+0.033) # in €/MW
        self.network.add("Generator", 
                    "Wind Generator", 
                    p_nom_extendable=True,
                    bus="Electricity Bus", 
                    carrier="Wind", 
                    capital_cost = capital_cost_wind,
                    p_max_pu=self.wind_cf.values)

        capital_cost_solar = annuity(25,0.07)*425000*(1+0.03) # in €/MW
        self.network.add("Generator", 
                    "Solar Generator", 
                    p_nom_extendable=True,
                    bus="Electricity Bus", 
                    carrier="Solar", 
                    capital_cost = capital_cost_solar,
                    p_max_pu=self.solar_cf.values)

        capital_cost_OCGT = annuity(25,0.07)*560000*(1+0.033) # in €/MW
        fuel_cost = 21.6 # in €/MWh_th
        efficiency = 0.39 # MWh_elec/MWh_th
        marginal_cost_OCGT = fuel_cost/efficiency # in €/MWh_el
        self.network.add("Generator",
                    "OCGT",
                    bus="Electricity Bus",
                    p_nom_extendable=True,
                    carrier="Gas",
                    capital_cost = capital_cost_OCGT,
                    marginal_cost = marginal_cost_OCGT)

        capital_cost_coal = annuity(25,0.07)*3711000*(1+0.033) # in €/MW
        fuel_cost_coal = 15.0 # in €/MWh_th
        efficiency_coal = 0.35 # MWh_elec/MWh_th
        marginal_cost_coal = fuel_cost_coal/efficiency_coal # in €/MWh_el
        
        self.network.add("Generator",
                    "Coal",
                    bus="Electricity Bus",
                    p_nom_extendable=True,
                    carrier="Coal",
                    capital_cost = capital_cost_coal,
                    marginal_cost = marginal_cost_coal)
        
        self.network.sanitize()

    def optimize_network(self):
        self.network.optimize(
            solver_name="gurobi",
            solver_options={"OutputFlag": 0},
            include_objective_constant=True  # explicitly match current behavior
        )
        
    def display_results(self):

        capacities = self.network.generators.p_nom_opt
        dispatch = self.network.generators_t.p

        #print("Optimal capacities:")
        #print(capacities)

        #print("Optimal generation:")
        #print(dispatch)

        return dispatch, capacities
        

if __name__ == "__main__":
    
    ### LOADING DATA ###

    print("Loading data...")
    load, wind_cf, solar_cf = load_data("EE", 2017)

    print(f"Load series length: {len(load)}")
    print(f"Wind CF series length: {len(wind_cf)}")
    print(f"Solar CF series length: {len(solar_cf)}")
    hours = pd.date_range('2017-01-01 00:00Z',
                                '2017-12-31 23:00Z',
                                freq='h')
    
    ### BUILD NETWORK ###
    
    network = Network(load, wind_cf, solar_cf, hours)
    network.build_network()
    network.optimize_network()
    dispatch, _ = network.display_results()
    
    ### PLOTS ###
    
    # Plot one week in January
    january_week_mask = (hours >= '2017-01-01') & (hours < '2017-01-08')
    january_week = hours[january_week_mask]
    
    plot_dispatch(january_week, dispatch[january_week_mask], load[january_week_mask], 'Optimal Hourly Dispatch for One Week in January 2017')
    
    # Plot one week in July
    july_week_mask = (hours >= '2017-07-01') & (hours < '2017-07-08')
    july_week = hours[july_week_mask]
    
    plot_dispatch(july_week, dispatch[july_week_mask], load[july_week_mask], 'Optimal Hourly Dispatch for One Week in July 2017')
    
    plot_annual_energy_mix(dispatch, 'Annual Energy Mix for 2017')

    plot_duration_curve(dispatch, 'Duration Curve for 2017')