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
    
    def build_network(self, storage=False, transmission=False, external=False):

        # PyPSA requires timezone-naive snapshots.
        snapshots = pd.DatetimeIndex(self.hours)
        if snapshots.tz is not None:
            snapshots = snapshots.tz_localize(None)
        self.network.set_snapshots(snapshots)
        # Add a bus
        self.network.add("Bus", "Estonia")

        # Add a load
        self.network.add("Load", 
                    "Estonia_Load",
                    bus="Estonia", 
                    p_set=self.load['EE'].values)
        self.network.loads_t.p_set

        # Add network carriers
        self.network.add("Carrier", "Wind")
        self.network.add("Carrier", "Solar")
        self.network.add("Carrier", "Gas", co2_emissions=0.19)
        self.network.add("Carrier", "Coal", co2_emissions=1.0)
        self.network.add("Carrier", "Nuclear")
        self.network.add("Carrier", "Hydro")

        # Add network generators
        
        # Onshore Wind
        # https://www.sciencedirect.com/science/article/pii/S0196890419309835?via%3Dihub
        capital_cost_wind = annuity(30,0.07)*910_000*(1+0.033) # in €/MW
        self.network.add("Generator", 
                    "Wind Generator", 
                    p_nom_extendable=True,
                    bus="Estonia", 
                    carrier="Wind", 
                    capital_cost = capital_cost_wind,
                    p_max_pu=self.wind_cf['EE'].values)
        
        # PV
        # https://www.sciencedirect.com/science/article/pii/S0196890419309835?via%3Dihub
        capital_cost_solar = annuity(25,0.07)*425_000*(1+0.03) # in €/MW
        self.network.add("Generator", 
                    "Solar Generator", 
                    p_nom_extendable=True,
                    bus="Estonia", 
                    carrier="Solar", 
                    capital_cost = capital_cost_solar,
                    p_max_pu=self.solar_cf['EE'].values)
        
        # OCGT Power Plant
        # https://www.sciencedirect.com/science/article/pii/S0196890419309835?via%3Dihub
        capital_cost_OCGT = annuity(25,0.07)*560_000*(1+0.033) # in €/MW
        fuel_cost = 21.6 # in €/MWh_th
        efficiency = 0.39 # MWh_elec/MWh_th
        marginal_cost_OCGT = fuel_cost/efficiency # in €/MWh_el
        self.network.add("Generator",
                    "OCGT",
                    bus="Estonia",
                    p_nom_extendable=True,
                    carrier="Gas",
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
                    "Coal",
                    bus="Estonia",
                    p_nom_extendable=True,
                    carrier="Coal",
                    capital_cost = capital_cost_coal,
                    marginal_cost = marginal_cost_coal)
        
        if storage:
            self.add_storage()
        if transmission:
            self.add_transmission()
        if external:
            self.add_external()

        
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
                        "Battery Storage",
                        bus="Estonia",
                        p_nom_extendable=True,
                        capital_cost=capital_cost,
                        marginal_cost=marginal_cost,
                        efficiency_store=efficiency_store,
                        efficiency_dispatch=efficiency_dispatch,
                        max_hours=max_hours)
        
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
        v = 400                 # nominal voltage kV 
        extendable = False      # fixed capacities

        self.network.add("Line",
                        "FIN-SWE",
                        bus0="Finland",
                        bus1="Sweden",
                        s_nom=cap_fin_swe,
                        s_nom_extendable=extendable,
                        x=x,
                        v_nom=v)

        self.network.add("Line",
                        "EST-FIN",
                        bus0="Estonia",
                        bus1="Finland",
                        s_nom=cap_est_fin,
                        s_nom_extendable=extendable,
                        x=x,
                        v_nom=v)

        self.network.add("Line",
                        "EST-SWE",
                        bus0="Estonia",
                        bus1="Sweden",
                        s_nom=cap_est_swe,
                        s_nom_extendable=extendable,
                        x=x,
                        v_nom=v)

        self.network.add("Line",
                        "EST-LAT",
                        bus0="Estonia",
                        bus1="Latvia",
                        s_nom=cap_est_lat,
                        s_nom_extendable=extendable,
                        x=x,
                        v_nom=v)

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
                    "Coal",
                    bus="Latvia",
                    p_nom_extendable=True,
                    carrier="Coal",
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
        
    def optimize_network(self):
        self.network.optimize(
            solver_name="gurobi",
            solver_options={"OutputFlag": 0},
            include_objective_constant=True  # explicitly match current behavior
        )
        
    def display_results(self):

        capacities = self.network.generators.p_nom_opt
        dispatch = self.network.generators_t.p.copy()

        storage_data = None
        if not self.network.storage_units.empty:
            storage_p = self.network.storage_units_t.p.copy()
            storage_soc = self.network.storage_units_t.state_of_charge.copy()

            storage_name = self.network.storage_units.index[0]
            dispatch["Battery Storage Discharge"] = storage_p[storage_name].clip(lower=0)
            dispatch["Battery Storage Charge"] = (-storage_p[storage_name].clip(upper=0))
            dispatch["Battery Storage SoC"] = storage_soc[storage_name]

            storage_data = pd.DataFrame(
                {
                    "Battery Storage Discharge": dispatch["Battery Storage Discharge"],
                    "Battery Storage Charge": dispatch["Battery Storage Charge"],
                    "Battery Storage SoC": dispatch["Battery Storage SoC"],
                },
                index=dispatch.index,
            )
            
            

        return dispatch, capacities, storage_data
        
        

if __name__ == "__main__":
    
    ### LOADING DATA ###

    print("Loading data...")
    load, wind_cf, solar_cf = load_data(year=2017)

    print(f"Load series length: {len(load)}")
    print(f"Wind CF series length: {len(wind_cf)}")
    print(f"Solar CF series length: {len(solar_cf)}")
    hours = pd.date_range('2017-01-01 00:00',
                                '2017-12-31 23:00',
                                freq='h')
    
    ### BUILD NETWORK ###
    
    network = Network(load, wind_cf, solar_cf, hours)
    network.build_network(storage=True, transmission=True, external=True)
    network.optimize_network()
    dispatch, capacities, storage_data = network.display_results()
    
    
    




