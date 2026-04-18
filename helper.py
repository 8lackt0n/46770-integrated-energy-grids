
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
