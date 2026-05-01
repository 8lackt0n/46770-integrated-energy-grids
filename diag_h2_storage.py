from data_loader import load_data
from network import Network
import pandas as pd


def main():
    pd.set_option("display.width", 260)
    pd.set_option("display.max_columns", 80)

    load, wind_cf, solar_cf = load_data(year=2017)
    hours = pd.date_range("2017-01-01 00:00", "2017-12-31 23:00", freq="h", tz="UTC")

    network = Network(load, wind_cf, solar_cf, hours=hours)
    network.build_network(
        storage=True,
        transmission=True,
        external=True,
        h2=True,
        co2_limit=True,
        limit=28_000_000 * 0.2,
    )
    network.optimize_network()

    dispatch, capacities = network.save_results()

    cols = [
        col for col in dispatch.columns
        if any(token in col for token in [
            "Battery Charge Estonia",
            "Battery Discharge Estonia",
            "Battery SoC Estonia",
            "Electrolyzer",
            "H2 Turbine",
            "H2 Storage SoC",
        ])
    ]

    window = dispatch.loc["2017-01-04":"2017-01-05 23:00", cols]
    print("COLUMNS:", cols)
    print(window.to_string())

    print("\nCOUNTRY H2 SUMMARY")
    for country in ["Estonia", "Latvia", "Sweden", "Finland"]:
        elec = [col for col in dispatch.columns if country in col and "Electrolyzer" in col]
        turb = [col for col in dispatch.columns if country in col and "H2 Turbine" in col]
        soc = [col for col in dispatch.columns if country in col and "H2 Storage SoC" in col]

        elec_total = float(dispatch[elec].sum().sum()) if elec else 0.0
        turb_total = float(dispatch[turb].sum().sum()) if turb else 0.0
        soc_max = float(dispatch[soc].max().max()) if soc else 0.0

        print(f"{country}: electrolyzer_total={elec_total:.1f} MW, turbine_total={turb_total:.1f} MW, max_soc={soc_max:.1f} MWh")

    print("\nBATTERY VS H2 OVERLAP")
    battery_charge = dispatch["Battery Charge Estonia"] if "Battery Charge Estonia" in dispatch.columns else pd.Series(0, index=dispatch.index)
    battery_discharge = dispatch["Battery Discharge Estonia"] if "Battery Discharge Estonia" in dispatch.columns else pd.Series(0, index=dispatch.index)
    h2_electrolyzer = dispatch[[col for col in dispatch.columns if "Estonia" in col and "Electrolyzer" in col]].sum(axis=1) if any("Estonia" in col and "Electrolyzer" in col for col in dispatch.columns) else pd.Series(0, index=dispatch.index)
    h2_turbine = dispatch[[col for col in dispatch.columns if "Estonia" in col and "H2 Turbine" in col]].sum(axis=1) if any("Estonia" in col and "H2 Turbine" in col for col in dispatch.columns) else pd.Series(0, index=dispatch.index)

    overlap = pd.DataFrame({
        "battery_charge": battery_charge,
        "battery_discharge": battery_discharge,
        "h2_electrolyzer_estonia": h2_electrolyzer,
        "h2_turbine_estonia": h2_turbine,
    })
    overlap = overlap.loc["2017-01-04":"2017-01-05 23:00"]
    overlap["any_h2_active"] = (overlap["h2_electrolyzer_estonia"].abs() + overlap["h2_turbine_estonia"].abs()) > 0
    overlap["battery_simultaneous"] = (overlap["battery_charge"] > 0) & (overlap["battery_discharge"] > 0)
    print(overlap.to_string())


if __name__ == "__main__":
    main()