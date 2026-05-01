import pandas as pd

def annuity(n, r):
    if r > 0:
        return r / (1 - 1/(1+r)**n)
    else:
        return 1/n
    
def annualize(value, year_from, year_to, rate=0.07):
    t = year_to - year_from
    return value * (1 + rate) ** t

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
        "Battery Discharge Estonia",
    ]

    power_max_candidates = [float(load_series.max())]
    available_columns = [col for col in dispatch_power_columns if col in dispatch_df.columns]
    if available_columns:
        total_power = dispatch_df[available_columns].sum(axis=1)
        power_max_candidates.append(float(total_power.max()))

    return max(power_max_candidates) * 1.05

NODE_ALIASES = {
    "Finland": "FI",
    "Sweden": "SE",
    "Latvia": "LV",
    "Estonia": "EE",
    "FIN": "FI",
    "SWE": "SE",
    "LAT": "LV",
    "EST": "EE",
}

def get_node(col):
    """Infer node from last word in dispatch column."""
    last = col.split()[-1]
    return NODE_ALIASES.get(last, last)


def calculate_imbalances(dispatch, load):
    """
    Imbalance = generation + discharge - load - charge

    Ignores:
    - Battery SoC
    - transmission lines like EST-FIN
    - CHP heat output
    """

    imbalances = pd.DataFrame(index=dispatch.index)

    nodes = load.columns

    for node in nodes:
        generation_cols = []
        charge_cols = []
        discharge_cols = []

        for col in dispatch.columns:
            # skip line flows and state variables
            if "-" in col:
                continue
            if "SoC" in col:
                continue
            if "Heat" in col:
                continue

            col_node = get_node(col)

            if col_node != node:
                continue

            if "Charge" in col:
                charge_cols.append(col)
            elif "Discharge" in col:
                discharge_cols.append(col)
            else:
                generation_cols.append(col)

        generation = dispatch[generation_cols].sum(axis=1) if generation_cols else 0
        charge = dispatch[charge_cols].sum(axis=1) if charge_cols else 0
        discharge = dispatch[discharge_cols].sum(axis=1) if discharge_cols else 0

        imbalances[node] = generation + discharge - load[node] - charge

    return imbalances