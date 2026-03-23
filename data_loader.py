# data_loader.py

import pandas as pd
import pycountry


# ============================
# HARDCODED FILE PATHS
# ============================

LOAD_FILE = "data/time_series_60min_singleindex_filtered.csv"
WIND_FILE = "data/onshore_wind_1979-2017.csv"
SOLAR_FILE = "data/pv_optimal.csv"



def alpha2_to_alpha3(alpha2="EE"):
    country = pycountry.countries.get(alpha_2=alpha2.upper())
    if country:
        return country.alpha_3
    else:
        return None

def load_data(year=2016):
    
    """
    Loads:
    - Electricity demand from OPSD-style dataset
    - Wind capacity factors
    - Solar capacity factors

    Returns:
    --------
    load : pd.Series
    wind_cf : pd.Series
    solar_cf : pd.Series
    """
    
    countries = ["EE", "LV", "FI", "SE"]

    df_load = pd.read_csv(LOAD_FILE)
    df_load["utc_timestamp"] = pd.to_datetime(df_load["utc_timestamp"])
    df_load = df_load.set_index("utc_timestamp")

    df_load = df_load[df_load.index.year == year]
    
    load = pd.concat(
        [df_load[f"{c}_load_actual_entsoe_transparency"].ffill().rename(c) for c in countries],
        axis=1
    )


    # ============================
    # 2) LOAD WIND CF
    # ============================

    df_wind = pd.read_csv(WIND_FILE, sep=";", index_col=0)
    df_wind.index = pd.to_datetime(df_wind.index)

    wind_cf = pd.concat(
        [df_wind[alpha2_to_alpha3(c)][df_wind.index.year == year].rename(c) for c in countries],
        axis=1
    )
        


    # ============================
    # 3) LOAD SOLAR CF
    # ============================

    df_solar = pd.read_csv(SOLAR_FILE, sep=";", index_col=0)
    df_solar.index = pd.to_datetime(df_solar.index)

    solar_cf = pd.concat(
        [df_solar[alpha2_to_alpha3(c)][df_solar.index.year == year].rename(c) for c in countries],
        axis=1
    )


    # ============================
    # 4) ALIGN INDEXES
    # ============================

    # Make sure all time series have identical timestamps
    snapshots = load.index

    wind_cf = wind_cf.reindex(snapshots).fillna(0)
    solar_cf = solar_cf.reindex(snapshots).fillna(0)


    return load, wind_cf, solar_cf

if __name__ == "__main__":
    load, wind_cf, solar_cf = load_data()
    print(load)
    print(wind_cf)
    print(solar_cf)