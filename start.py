# main.py

import pandas as pd
from data_loader import load_data
import helper


print("Loading data...")
load, wind_cf, solar_cf = load_data("EE", 2017)

print(f"Load series length: {len(load)}")
print(f"Wind CF series length: {len(wind_cf)}")
print(f"Solar CF series length: {len(solar_cf)}")





