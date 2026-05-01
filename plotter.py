import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

# def _dispatch_series(df):
#     colors, _ = color_palette()
#     series = [
#         ("Wind Generator Estonia", "Wind Production [MWh]", colors[13]),
#         ("Solar Generator Estonia", "PV Production [MWh]", colors[12]),
#         ("OCGT Estonia", "Gas Production [MWh]", colors[14]),
#         ("Coal Estonia", "Coal Production [MWh]", colors[15]),
#     ]

#     if "Battery Storage Discharge" in df.columns:
#         series.append(("Battery Storage Discharge", "Battery Discharge [MWh]", colors[9]))

#     return series


def color_palette():
    background_color = "#FAEEDD"
    color_palette = [
        "#B00020",
        "#D62828",
        "#E04A2E",
        "#F26430",
        "#F77F4F",
        "#F9A45C",
        "#FBBF6B",
        "#F5C07A",
        "#F2D8A0",
        "#0F4A43",
        "#66C2A4",
        "#A0E7D6",
        "#FBBF6B",  # PV
        "#5C97D9",  # Wind
        "#21B582",  # Gas
        "#7D7878",  # Coal
    ]
    return color_palette, background_color


def _contrast_text_color(fill_color):
    r, g, b = matplotlib.colors.to_rgb(fill_color)
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return "black" if luminance > 0.55 else "white"

def save_plot(file_name):
    os.makedirs("plots", exist_ok=True)
    output_path = os.path.join("plots", f"{file_name}.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')

def plot_annual_energy_mix(df, title, show=False, save=True):
    colors, background_color = color_palette()

    components = [
        ("OCGT Estonia", "Gas", colors[14]),
        ("Coal Estonia", "Coal", colors[15]),
        ("Solar Generator Estonia", "Solar", colors[12]),
        ("Wind Generator Estonia", "Wind", colors[13]),

    ]

    if "Battery Discharge Estonia" in df.columns:
        components.append(("Battery Discharge Estonia", "Battery Discharge", colors[9]))

    # Add net imports if the annual balance is positive.
    import_columns = [col for col in df.columns if "EST" in col and "-" in col]
    net_import_to_estonia = 0.0
    for col in import_columns:
        flow = df[col].sum()
        left, right = col.split("-")

        if left == "EST":
            net_import_to_estonia -= flow
        elif right == "EST":
            net_import_to_estonia += flow

    if net_import_to_estonia > 0:
        components.append(("Net Import to Estonia", "Net Imports", colors[10]))
    

    values = [df[col].sum() if col in df.columns else 0.0 for col, _, _ in components if col != "Net Import to Estonia"]
    
    # Handle net imports specially since it's not a real column
    if net_import_to_estonia > 0:
        values.append(net_import_to_estonia)
    
    labels = [label for _, label, _ in components]
    pie_colors = [color for _, _, color in components]

    total_val = sum(values) if values else 1.0
    labels_with_totals = [f"{label}\n({val:.0f} MWh, {100*val/total_val:.1f}%)" for label, val in zip(labels, values)]
    
    fig, ax = plt.subplots(figsize=(14, 8))
    fig.patch.set_facecolor(background_color)
    ax.set_facecolor(background_color)
    
    ax.pie(
        values,
        labels=labels_with_totals,
        colors=pie_colors,
        startangle=90,
        textprops={'fontsize': 10, 'color': 'black', 'fontweight': 'bold'},
        wedgeprops={'linewidth': 0.5, 'edgecolor': 'white'},
        pctdistance=0.75,
    )
    ax.set_aspect('equal')
    
    
    ax.text(0.0, 1.07, title, transform=ax.transAxes, fontsize=14, color='black', ha='left', fontweight='bold')
    subtitle_parts = ["Wind", "Solar", "Gas", "Coal"]
    if "Battery Discharge Estonia" in df.columns:
        subtitle_parts.append("Battery Discharge")
    if net_import_to_estonia > 0:
        subtitle_parts.append("Net Imports")
    annual_subtitle = "Total " + ", ".join(subtitle_parts[:-1]) + (
        f", and {subtitle_parts[-1]}" if len(subtitle_parts) > 1 else subtitle_parts[0]
    ) + " in MWh"

    ax.text(0.0, 1.01, annual_subtitle, transform=ax.transAxes, fontsize=10, color='black', ha='left')
    
    if save:
        fig_title = title.replace(" ", "_").lower()
        print("Saving:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()

def plot_country_balance(dispatch, load, title, show=False, save=True):
    """
    Plot a country-level annual energy balance.

    Positive values are generation, imports, and battery discharge.
    Negative values are load, battery charge, and exports.
    """
    colors, background_color = color_palette()

    countries = ["Estonia", "Latvia", "Sweden", "Finland"]
    load_cols = {"Estonia": "EE", "Finland": "FI", "Sweden": "SE", "Latvia": "LV"}

    generation_components = {
        "Estonia": ["Wind Generator Estonia", "Solar Generator Estonia", "OCGT Estonia", "Coal Estonia"],
        "Finland": ["Wind Generator Finland", "Nuclear Finland"],
        "Sweden": ["Wind Generator Sweden", "Hydro Sweden"],
        "Latvia": ["Wind Generator Latvia", "Coal Latvia"],
    }

    battery_discharge_cols = {
        country: f"Battery Discharge {country}" for country in countries
    }
    battery_charge_cols = {
        country: f"Battery Charge {country}" for country in countries
    }

    generation = {}
    battery_discharge = {}
    battery_charge = {}
    demand = {}
    imports = {country: 0.0 for country in countries}
    exports = {country: 0.0 for country in countries}

    for country in countries:
        generation[country] = sum(float(dispatch[col].sum()) for col in generation_components[country] if col in dispatch.columns)
        battery_discharge[country] = float(dispatch[battery_discharge_cols[country]].sum()) if battery_discharge_cols[country] in dispatch.columns else 0.0
        battery_charge[country] = float(dispatch[battery_charge_cols[country]].sum()) if battery_charge_cols[country] in dispatch.columns else 0.0
        demand[country] = float(load[load_cols[country]].sum()) if isinstance(load, pd.DataFrame) and load_cols[country] in load.columns else 0.0

    line_pairs = [
        ("FIN-SWE", "Finland", "Sweden"),
        ("EST-FIN", "Estonia", "Finland"),
        ("EST-SWE", "Estonia", "Sweden"),
        ("EST-LAT", "Estonia", "Latvia"),
    ]

    for line, left, right in line_pairs:
        if line not in dispatch.columns:
            continue

        flow = float(dispatch[line].sum())
        if flow > 0:
            exports[left] += flow
            imports[right] += flow
        elif flow < 0:
            exports[right] += -flow
            imports[left] += -flow

    source_components = [
        ("Generation", colors[10]),
        ("Net imports", colors[1]),
        ("Battery discharge", colors[9]),
    ]
    sink_components = [
        ("Load", colors[15]),
        ("Battery charge", colors[8]),
        ("Net exports", colors[3]),
    ]

    fig, ax = plt.subplots(figsize=(13, 7))
    fig.patch.set_facecolor(background_color)
    ax.set_facecolor(background_color)

    y = np.arange(len(countries))

    positive_stack = np.zeros(len(countries))
    negative_stack = np.zeros(len(countries))

    source_values = {
        "Generation": np.array([generation[c] for c in countries]),
        "Net imports": np.array([imports[c] for c in countries]),
        "Battery discharge": np.array([battery_discharge[c] for c in countries]),
    }
    sink_values = {
        "Load": np.array([demand[c] for c in countries]),
        "Battery charge": np.array([battery_charge[c] for c in countries]),
        "Net exports": np.array([exports[c] for c in countries]),
    }

    for label, color in source_components:
        values = source_values[label]
        ax.barh(
            y,
            values,
            left=positive_stack,
            color=color,
            edgecolor="white",
            linewidth=0.5,
            label=label,
        )
        positive_stack += values

    for label, color in sink_components:
        values = sink_values[label]
        ax.barh(
            y,
            -values,
            left=negative_stack,
            color=color,
            edgecolor="white",
            linewidth=0.5,
            label=label,
        )
        negative_stack -= values

    max_extent = max(np.max(np.abs(positive_stack)), np.max(np.abs(negative_stack)), 1.0)

    ax.axvline(0, color="black", linewidth=1.0)
    ax.set_yticks(y)
    ax.set_yticklabels(countries)
    ax.set_xlabel("Annual energy [MWh]")
    ax.set_xlim(-1.15 * max_extent, 1.15 * max_extent)
    ax.invert_yaxis()

    ax.text(
        0.0, 1.07, title,
        transform=ax.transAxes,
        fontsize=14,
        color="black",
        ha="left",
        fontweight="bold",
    )

    ax.text(
        0.0, 1.01,
        "Positive values are generation, imports, and discharge. Negative values are load, charge, and exports.",
        transform=ax.transAxes,
        fontsize=10,
        color="black",
        ha="left",
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=3,
        frameon=True,
        facecolor="white",
        framealpha=1,
    )

    fig.subplots_adjust(bottom=0.22)

    if save:
        fig_title = title.replace(" ", "_").lower()
        print("Saving:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()

def plot_duration_curve(df, title, show=False, save=True):

    colors, background_color = color_palette()

    series = [
        ("Wind Generator Estonia", "Wind", colors[13]),
        ("Solar Generator Estonia", "Solar", colors[12]),
        ("OCGT Estonia", "Gas", colors[14]),
        ("Coal Estonia", "Coal", colors[15]),
    ]

    if "Battery Discharge Estonia" in df.columns:
        series.append(("Battery Discharge Estonia", "Battery Discharge", colors[9]))

    fig, ax = plt.subplots(figsize=(12, 4))
    fig.patch.set_facecolor(background_color)
    ax.set_facecolor(background_color)

    for col, label, color in series:
        if col in df.columns:
            sorted_values = df[col].sort_values(ascending=False).reset_index(drop=True)
            hours = range(len(sorted_values))
            ax.plot(hours, sorted_values, label=label, color=color)

    ax.set_xlabel("Hours (sorted)", labelpad=5)
    ax.set_ylabel("Generation [MW]")

    ax.text(
        0.0, 1.07,
        title,
        transform=ax.transAxes,
        fontsize=14,
        color="black",
        ha="left",
        fontweight="bold"
    )

    subtitle = "Sorted hourly generation for each technology"
    if "Battery Discharge Estonia" in df.columns:
        subtitle = "Sorted hourly generation and battery discharge for each technology"

    ax.text(
        0.0, 1.01,
        subtitle,
        transform=ax.transAxes,
        fontsize=10,
        color="black",
        ha="left"
    )

    ax.legend(
        bbox_to_anchor=(0.5, -0.16),
        ncol=len(series),
        loc="upper center",
        frameon=True,
        facecolor="white",
        framealpha=1,
    )

    fig.subplots_adjust(bottom=0.25)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    if save:
        fig_title = title.replace(" ", "_").lower()
        print("Saving:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()

def plot_capacity_variability(capacity_df, title, show=False, save=True):

    colors, background_color = color_palette()

    avg = capacity_df.mean()
    std = capacity_df.std()

    fig, ax = plt.subplots(figsize=(12, 4))
    fig.patch.set_facecolor(background_color)
    ax.set_facecolor(background_color)

    ax.bar(
        avg.index,
        avg.values,
        yerr=std.values,
        capsize=5,
        color=[colors[13], colors[12], colors[14], colors[15]]
    )

    ax.set_ylabel("Installed Capacity [MW]")

    ax.text(0.0, 1.07,
        title,
        transform=ax.transAxes,
        fontsize=14,
        fontweight="bold"
    )

    ax.text(0.0, 1.01,
        "Error bars show standard deviation across weather years",
        transform=ax.transAxes,
        fontsize=10
    )

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    if save:
        fig_title = title.replace(" ", "_").lower()
        print("Saving:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()

def plot_storage_operation(time_index, df, title, show=False, save=True):
    import numpy as np
    import matplotlib.pyplot as plt

    colors, background_color = color_palette()

    fig, ax1 = plt.subplots(figsize=(12, 4))
    fig.patch.set_facecolor(background_color)
    ax1.set_facecolor(background_color)

    # Get columns safely
    charge = np.asarray(df["Battery Charge Estonia"]) if "Battery Charge Estonia" in df.columns else np.zeros(len(time_index))
    discharge = np.asarray(df["Battery Discharge Estonia"]) if "Battery Discharge Estonia" in df.columns else np.zeros(len(time_index))
    soc = np.asarray(df["Battery SoC Estonia"]) if "Battery SoC Estonia" in df.columns else np.zeros(len(time_index))

    # Plot discharge positive, charge negative
    ax1.step(
        time_index,
        discharge,
        where="mid",
        label="Battery Discharge [MW]",
        color=colors[9],
        linewidth=1.8,
    )

    ax1.step(
        time_index,
        -charge,
        where="mid",
        label="Battery Charge [MW]",
        color=colors[1],
        linewidth=1.8,
    )

    # Optional fill for readability
    ax1.fill_between(
        time_index, 0, discharge,
        step="mid",
        alpha=0.25,
        color=colors[9]
    )
    ax1.fill_between(
        time_index, 0, -charge,
        step="mid",
        alpha=0.25,
        color=colors[1]
    )

    ax1.axhline(0, color="black", linewidth=0.8)
    ax1.set_ylabel("Power [MW]")

    # Secondary axis for SoC
    ax2 = ax1.twinx()
    ax2.step(
        time_index,
        soc,
        where="mid",
        label="Battery State of Charge [MWh]",
        color="black",
        linewidth=2,
        linestyle=":"
    )
    ax2.set_ylabel("State of Charge [MWh]")

    # Titles
    ax1.text(
        0.0, 1.07, title,
        transform=ax1.transAxes,
        fontsize=14,
        color="black",
        ha="left",
        fontweight="bold"
    )
    ax1.text(
        0.0, 1.01,
        "Battery charging, discharging, and state of charge",
        transform=ax1.transAxes,
        fontsize=10,
        color="black",
        ha="left"
    )

    # Legend
    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(
        lines_1 + lines_2,
        labels_1 + labels_2,
        bbox_to_anchor=(0.5, -0.16),
        ncol=3,
        loc="upper center",
        frameon=True,
        facecolor="white",
        framealpha=1,
    )

    # Styling
    ax1.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # Symmetric power axis
    max_power = max(np.max(charge), np.max(discharge), 1)
    ax1.set_ylim(-1.15 * max_power, 1.15 * max_power)

    # Optional SoC limits
    if np.max(soc) > 0:
        ax2.set_ylim(0, 1.1 * np.max(soc))

    fig.subplots_adjust(bottom=0.25)

    if save:
        fig_title = title.replace(" ", "_").lower()
        print("Saving:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()

def plot_h2_storage_operation(time_index, df, title, show=False, save=True):
    colors, background_color = color_palette()

    fig, ax1 = plt.subplots(figsize=(12, 4))
    fig.patch.set_facecolor(background_color)
    ax1.set_facecolor(background_color)

    # H2 charging/discharging proxy:
    # - Electrolyzers consume electricity to charge H2 storage.
    # - H2 turbines convert stored H2 back to electricity (discharge proxy).
    electrolyzer_cols = [col for col in df.columns if "Electrolyzer" in col]
    turbine_cols = [col for col in df.columns if "H2 Turbine" in col]
    h2_soc_cols = [col for col in df.columns if "H2 Storage" in col and "SoC" in col]

    charge = np.zeros(len(time_index))
    for col in electrolyzer_cols:
        charge += np.asarray(df[col])

    discharge = np.zeros(len(time_index))
    for col in turbine_cols:
        discharge += np.asarray(df[col])

    soc = np.zeros(len(time_index))
    for col in h2_soc_cols:
        soc += np.asarray(df[col])

    ax1.step(
        time_index,
        discharge,
        where="mid",
        label="H2-to-Power (Turbine) [MW]",
        color="#2E7D32",
        linewidth=1.8,
    )

    ax1.step(
        time_index,
        -charge,
        where="mid",
        label="Power-to-H2 (Electrolyzer) [MW]",
        color="#EF6C00",
        linewidth=1.8,
    )

    ax1.fill_between(
        time_index, 0, discharge,
        step="mid",
        alpha=0.22,
        color="#2E7D32"
    )
    ax1.fill_between(
        time_index, 0, -charge,
        step="mid",
        alpha=0.22,
        color="#EF6C00"
    )

    ax1.axhline(0, color="black", linewidth=0.8)
    ax1.set_ylabel("Power [MW]")

    ax2 = ax1.twinx()
    ax2.step(
        time_index,
        soc,
        where="mid",
        label="H2 Storage State of Charge [MWh]",
        color="#1565C0",
        linewidth=2,
        linestyle=":",
    )
    ax2.set_ylabel("State of Charge [MWh]")

    ax1.text(
        0.0, 1.07, title,
        transform=ax1.transAxes,
        fontsize=14,
        color="black",
        ha="left",
        fontweight="bold"
    )
    ax1.text(
        0.0, 1.01,
        "H2 storage operation: power-to-H2, H2-to-power, and H2 state of charge",
        transform=ax1.transAxes,
        fontsize=10,
        color="black",
        ha="left"
    )

    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(
        lines_1 + lines_2,
        labels_1 + labels_2,
        bbox_to_anchor=(0.5, -0.16),
        ncol=3,
        loc="upper center",
        frameon=True,
        facecolor="white",
        framealpha=1,
    )

    ax1.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    max_power = max(np.max(charge), np.max(discharge), 1)
    ax1.set_ylim(-1.15 * max_power, 1.15 * max_power)

    if np.max(soc) > 0:
        ax2.set_ylim(0, 1.1 * np.max(soc))

    fig.subplots_adjust(bottom=0.25)

    if save:
        fig_title = title.replace(" ", "_").lower()
        print("Saving:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()

def plot_capacities_vs_co2_limits(scenario_results, base_co2, title, show=False, save=True):
    

    colors, background_color = color_palette()

    components = [
        ("Wind Generator Estonia", "Wind", colors[13]),
        ("Solar Generator Estonia", "Solar", colors[12]),
        ("OCGT Estonia", "Gas", colors[14]),
        ("Coal Estonia", "Coal", colors[15]),
        ("Battery Storage Estonia", "Battery", colors[9]),
    ]

    rows = []
    for scenario in scenario_results:
        capacities = scenario["capacities"]
        limit = scenario["co2_limit"]

        row = {"co2_limit": limit}

        # Handle DataFrame with column p_nom_opt
        if isinstance(capacities, pd.DataFrame):
            if "p_nom_opt" in capacities.columns:
                capacities_series = capacities["p_nom_opt"]
            else:
                capacities_series = capacities.iloc[:, 0]
        else:
            capacities_series = capacities

        for comp_name, label, _ in components:
            row[label] = capacities_series.get(comp_name, 0.0)

        rows.append(row)

    df_plot = pd.DataFrame(rows)

    df_plot = df_plot.sort_values("co2_limit", ascending=False).reset_index(drop=True)
    df_plot["co2_label"] = [f"{(1 - x / base_co2) * 100:.0f}% reduction" for x in df_plot["co2_limit"]
]

    labels = [label for _, label, _ in components]
    stack_colors = [color for _, _, color in components]

    fig, ax = plt.subplots(figsize=(14, 5))
    fig.patch.set_facecolor(background_color)
    ax.set_facecolor(background_color)

    bottom = np.zeros(len(df_plot))

    for label, color in zip(labels, stack_colors):
        values = df_plot[label].values
        
        bars = ax.bar(
            df_plot["co2_label"],
            values,
            bottom=bottom,
            label=label,
            color=color,
            edgecolor="white",
            linewidth=0.5
        )

        # Add labels inside each segment
        for i, (bar, value) in enumerate(zip(bars, values)):
            if value > 0:  # avoid cluttering with zeros
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bottom[i] + value / 2,   # center vertically in segment
                    f"{value:.0f}",         # format as integer
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="black"
                )

        bottom += values

    ax.text(
        0.0, 1.07, title,
        transform=ax.transAxes,
        fontsize=14,
        color="black",
        ha="left",
        fontweight="bold"
    )

    ax.text(
        0.0, 1.01,
        "Installed capacity by technology for each CO2 reduction target in MW",
        transform=ax.transAxes,
        fontsize=10,
        color="black",
        ha="left"
    )

    ax.set_xlabel("CO2 Reduction Compared to Base Scenario")
    ax.set_ylabel("Installed capacity [MW]")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=5,
        frameon=True,
        facecolor="white",
        framealpha=1,
    )

    fig.subplots_adjust(right=0.82)

    if save:
        fig_title = title.replace(" ", "_").lower()
        print("Saving:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()
        
def plot_total_transmission_comparison(transmission_df, title, show=False, save=True):
    colors, background_color = color_palette()

    h2_columns = [
        "FIN-SWE H2 Pipeline",
        "EST-FIN H2 Pipeline",
        "EST-SWE H2 Pipeline",
        "EST-LAT H2 Pipeline",
    ]

    electrical_columns = [
        "FIN-SWE",
        "EST-FIN",
        "EST-SWE",
        "EST-LAT",
    ]

    # Keep only columns that actually exist
    h2_columns_existing = [col for col in h2_columns if col in transmission_df.columns]
    electrical_columns_existing = [col for col in electrical_columns if col in transmission_df.columns]

    total_h2 = transmission_df[h2_columns_existing].abs().sum().sum() / 1000 if h2_columns_existing else 0.0
    total_electric = transmission_df[electrical_columns_existing].abs().sum().sum() / 1000 if electrical_columns_existing else 0.0

    plot_df = pd.DataFrame({
        "Transmission Type": ["Electrical", "H2"],
        "Total Flow": [total_electric, total_h2]
    })

    bar_colors = [colors[0], colors[10]]

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor(background_color)
    ax.set_facecolor(background_color)

    ax.bar(
        plot_df["Transmission Type"],
        plot_df["Total Flow"],
        color=bar_colors,
        edgecolor="white",
        linewidth=0.5
    )

    ax.text(
        0.0, 1.07, title,
        transform=ax.transAxes,
        fontsize=14,
        color="black",
        ha="left",
        fontweight="bold"
    )

    ax.text(
        0.0, 1.01,
        "Total transported energy through electrical and H2 transmission in GWh",
        transform=ax.transAxes,
        fontsize=10,
        color="black",
        ha="left"
    )

    ax.set_ylabel("Total transmission [GWh]")
    ax.set_xlabel("")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    if save:
        fig_title = title.replace(" ", "_").lower()
        print("Saving:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()

def plot_capacity_mix(capacities, title, show=False, save=True):

    colors, background_color = color_palette()

    # Always take p_nom_opt column
    capacities = capacities["p_nom_opt"]

    # Handle duplicate indices
    capacities = capacities.groupby(capacities.index).sum()

    components = [
        ("Coal Estonia", "Coal", colors[15]),
        ("OCGT Estonia", "Gas", colors[14]),
        ("Wind Generator Estonia", "Wind", colors[13]),
        ("Solar Generator Estonia", "Solar", colors[12]),
    ]

    # Include battery capacity in the Estonia mix if present in the capacities index
    if any("Battery Storage" in idx for idx in capacities.index):
        components.append(("Battery Storage Estonia", "Battery", colors[9]))

    values = [capacities.loc[col] if col in capacities.index else 0.0 for col, _, _ in components]
    labels = [label for _, label, _ in components]
    stack_colors = [color for _, _, color in components]

    fig, ax = plt.subplots(figsize=(6, 6))
    fig.patch.set_facecolor(background_color)
    ax.set_facecolor(background_color)

    bottom = 0.0

    for value, label, color in zip(values, labels, stack_colors):
        if value == 0:
            continue

        bars = ax.bar(
            "Estonia",
            value,
            bottom=bottom,
            label=label,
            color=color,
            edgecolor="black",
            linewidth=0.5
        )

        # Annotate each stacked segment with its capacity value.
        bar = bars[0]
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bottom + value / 2,
            f"{value:.0f}",
            color=_contrast_text_color(color),
        )
        bottom += value

    ax.text(
        0.0, 1.07, title,
        transform=ax.transAxes,
        fontsize=14,
        color="black",
        ha="left",
        fontweight="bold"
    )

    subtitle = "Installed capacity mix [MW]"
    if "Battery Storage Estonia" in capacities.index:
        subtitle = "Installed capacity mix (incl. battery) [MW]"

    ax.text(
        0.0, 1.01,
        subtitle,
        transform=ax.transAxes,
        fontsize=10,
        color="black",
        ha="left"
    )

    ax.set_ylabel("Installed capacity [MW]")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.legend(
        loc="center left",
        bbox_to_anchor=(1.07, 0.5),
        frameon=True,
        facecolor="white",
        framealpha=1,
    )

    fig.subplots_adjust(right=0.95)

    if save:
        fig_title = title.replace(" ", "_").lower()
        print("Saving:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()

def plot_capacity_mix_by_country(capacities, title, show=False, save=True):

    colors, background_color = color_palette()

    countries = ["Estonia", "Finland", "Sweden", "Latvia"]

    technologies = [
        ("Nuclear", colors[8]),
        ("Coal", colors[15]),
        ("Gas", colors[14]),
        ("Hydro", colors[11]),
        ("Wind", colors[13]),
        ("Solar", colors[12]),
        ("Battery", colors[9]),
        ("H2 Electrolyzer", "#A7E3FF"),
        ("H2 Turbine", "#6EC6FF"),
        ("Heat Pump", colors[5]),
        ("CHP", colors[1])
    ]

    # If duplicate asset names exist, combine them
    capacities = capacities.groupby(capacities.index).sum(numeric_only=True)

    # Empty table: rows=countries, cols=technologies
    df_plot = pd.DataFrame(
        0.0,
        index=countries,
        columns=[tech for tech, _ in technologies]
    )

    # Iterate over asset rows
    for asset_name, row in capacities.iterrows():
        if not isinstance(asset_name, str):
            continue

        # Skip transmission lines/interconnectors
        if "-" in asset_name:
            continue

        # Find country
        country = None
        for c in countries:
            if asset_name.endswith(c):
                country = c
                break

        if country is None:
            continue

        # Use power capacity for the generic country mix. H2 storage is shown separately.
        p_nom = row["p_nom_opt"] if "p_nom_opt" in capacities.columns and pd.notna(row["p_nom_opt"]) else 0.0
        s_nom = row["s_nom_opt"] if "s_nom_opt" in capacities.columns and pd.notna(row["s_nom_opt"]) else 0.0

        # Classify technology
        if "Battery Storage" in asset_name:
            df_plot.loc[country, "Battery"] += p_nom
        elif "Electrolyzer" in asset_name:
            df_plot.loc[country, "H2 Electrolyzer"] += p_nom
        elif "H2 Turbine" in asset_name:
            df_plot.loc[country, "H2 Turbine"] += p_nom
        elif "Wind" in asset_name:
            df_plot.loc[country, "Wind"] += p_nom
        elif "Solar" in asset_name:
            df_plot.loc[country, "Solar"] += p_nom
        elif "OCGT" in asset_name:
            df_plot.loc[country, "Gas"] += p_nom
        elif "Coal" in asset_name:
            df_plot.loc[country, "Coal"] += p_nom
        elif "Nuclear" in asset_name:
            df_plot.loc[country, "Nuclear"] += p_nom
        elif "Hydro" in asset_name:
            df_plot.loc[country, "Hydro"] += p_nom
        elif "Heat Pump" in asset_name:
            df_plot.loc[country, "Heat Pump"] += p_nom
        elif "CHP" in asset_name:
            df_plot.loc[country, "CHP"] += p_nom
        
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor(background_color)
    ax.set_facecolor(background_color)

    x = np.arange(len(countries))
    bottom = np.zeros(len(countries))
    plotted = False
    totals = df_plot.sum(axis=1).values

    inside_label_fraction = 0.08
    inside_label_min_abs = 120.0
    outside_x_offset = 0.18
    outside_label_min_gap = max(np.max(totals) * 0.02, 25.0) if len(totals) > 0 else 25.0
    outside_label_positions = {i: [] for i in range(len(countries))}

    for tech, color in technologies:
        values = df_plot[tech].values
        if np.all(values == 0):
            continue

        bars = ax.bar(
            x,
            values,
            bottom=bottom,
            label=tech,
            color=color,
            edgecolor="white",
            linewidth=0.5,
        )

        for i, (bar, value) in enumerate(zip(bars, values)):
            if value <= 0:
                continue

            y_center = bottom[i] + value / 2
            inside_threshold = max(inside_label_min_abs, inside_label_fraction * totals[i])

            if value >= inside_threshold:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    y_center,
                    f"{value:.0f}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color=_contrast_text_color(color),

                )
            else:
                y_text = y_center
                while any(abs(y_text - y_used) < outside_label_min_gap for y_used in outside_label_positions[i]):
                    y_text += outside_label_min_gap
                outside_label_positions[i].append(y_text)

                x_center = bar.get_x() + bar.get_width() / 2
                x_right = bar.get_x() + bar.get_width()

                ax.annotate(
                    f"{value:.0f}",
                    xy=(x_right, y_center),
                    xytext=(x_center + outside_x_offset, y_text),
                    ha="left",
                    va="center",
                    fontsize=8,
                    color=_contrast_text_color(color),
                    arrowprops=dict(
                        arrowstyle="-",
                        color=_contrast_text_color(color),
                        linewidth=0.6,
                        shrinkA=0,
                        shrinkB=0,
                    ),
                )

        bottom += values
        plotted = True

    ax.set_xticks(x)
    ax.set_xticklabels(countries)
    ax.set_ylabel("Installed capacity [MW]")
    ax.set_xlim(-0.5, len(countries) - 0.5 + 0.85)

    ax.text(
        0.0, 1.07,
        title,
        transform=ax.transAxes,
        fontsize=14,
        color="black",
        ha="left",
        fontweight="bold",
    )

    ax.text(
        0.0, 1.01,
        "Installed generator and storage capacity by country [MW]",
        transform=ax.transAxes,
        fontsize=10,
        color="black",
        ha="left",
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    if plotted:
        ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.12),
            ncol=4,
            frameon=True,
            facecolor="white",
            framealpha=1,
        )

    fig.subplots_adjust(bottom=0.22)

    if save:
        fig_title = title.replace(" ", "_").lower()
        print("Saving:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()

def plot_h2_capacity_mix_by_country(network, title, show=False, save=True):

    colors, background_color = color_palette()
    countries = ["Estonia", "Finland", "Sweden", "Latvia"]

    power_technologies = [
        ("Electrolyzer", colors[10]),
        ("H2 Turbine", colors[14]),
    ]
    storage_color = colors[9]

    power_df = pd.DataFrame(0.0, index=countries, columns=[tech for tech, _ in power_technologies])
    storage_df = pd.Series(0.0, index=countries)

    if not network.links.empty:
        for asset_name, row in network.links.iterrows():
            if not isinstance(asset_name, str):
                continue
            # Include electrolyzers, H2 turbines and pipelines (names vary)
            if not ("H2" in asset_name or "Electrolyzer" in asset_name or "H2 Turbine" in asset_name or "H2 Pipeline" in asset_name):
                continue

            country = next((c for c in countries if asset_name.endswith(c)), None)
            if country is None:
                continue

            p_nom = row["p_nom_opt"] if "p_nom_opt" in network.links.columns and pd.notna(row["p_nom_opt"]) else 0.0

            if "Electrolyzer" in asset_name:
                power_df.loc[country, "Electrolyzer"] += p_nom
            elif "H2 Turbine" in asset_name:
                power_df.loc[country, "H2 Turbine"] += p_nom

    if not network.stores.empty:
        for asset_name, row in network.stores.iterrows():
            if not isinstance(asset_name, str) or "H2 Storage" not in asset_name:
                continue

            country = next((c for c in countries if asset_name.endswith(c)), None)
            if country is None:
                continue

            storage_energy = row["e_nom_opt"] if "e_nom_opt" in network.stores.columns and pd.notna(row["e_nom_opt"]) else 0.0
            storage_df.loc[country] += storage_energy

    fig, (ax_power, ax_storage) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    fig.patch.set_facecolor(background_color)
    ax_power.set_facecolor(background_color)
    ax_storage.set_facecolor(background_color)

    x = np.arange(len(countries))
    bottom = np.zeros(len(countries))

    for tech, color in power_technologies:
        values = power_df[tech].values
        if np.all(values == 0):
            continue

        bars = ax_power.bar(x, values, bottom=bottom, label=tech, color=color, edgecolor="white", linewidth=0.5)
        for i, (bar, value) in enumerate(zip(bars, values)):
            if value <= 0:
                continue
            ax_power.text(
                bar.get_x() + bar.get_width() / 2,
                bottom[i] + value / 2,
                f"{value:.0f}",
                ha="center",
                va="center",
                fontsize=8,
                color=_contrast_text_color(color),
            )
        bottom += values

    storage_values = storage_df.values
    storage_bars = ax_storage.bar(x, storage_values, color=storage_color, edgecolor="white", linewidth=0.5, label="H2 Storage")
    for bar, value in zip(storage_bars, storage_values):
        if value <= 0:
            continue
        ax_storage.text(
            bar.get_x() + bar.get_width() / 2,
            value / 2,
            f"{value:.0f}",
            ha="center",
            va="center",
            fontsize=8,
            color=_contrast_text_color(storage_color),
        )

    ax_power.set_ylabel("Installed power [MW]")
    ax_storage.set_ylabel("Storage energy [MWh]")
    ax_storage.set_xticks(x)
    ax_storage.set_xticklabels(countries)

    ax_power.text(0.0, 1.07, title, transform=ax_power.transAxes, fontsize=14, color="black", ha="left", fontweight="bold")
    ax_power.text(0.0, 1.01, "H2 converters: electrolyzers and turbines [MW]", transform=ax_power.transAxes, fontsize=10, color="black", ha="left")
    ax_storage.text(0.0, 1.01, "H2 storage shown as energy capacity [MWh]", transform=ax_storage.transAxes, fontsize=10, color="black", ha="left")

    ax_power.spines["top"].set_visible(False)
    ax_power.spines["right"].set_visible(False)
    ax_storage.spines["top"].set_visible(False)
    ax_storage.spines["right"].set_visible(False)

    ax_power.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=True, facecolor="white", framealpha=1)
    ax_storage.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=True, facecolor="white", framealpha=1)

    fig.tight_layout()

    if save:
        fig_title = title.replace(" ", "_").lower()
        print("Saving:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()


def plot_h2_scenarios_by_country(results, title, show=False, save=True):

    colors, background_color = color_palette()

    countries = ["Estonia", "Finland", "Sweden", "Latvia"]
    scenario_labels = [r["scenario"] for r in results]

    # Initialize data containers
    techs = ["Electrolyzer", "H2 Turbine", "H2 Storage"]
    data = {
        tech: pd.DataFrame(0.0, index=countries, columns=scenario_labels)
        for tech in techs
    }

    # Fill data
    for result in results:
        scen = result["scenario"]
        capacities = result["capacities"]

        for asset_name, row in capacities.iterrows():
            if not isinstance(asset_name, str):
                continue

            country = next((c for c in countries if asset_name.endswith(c)), None)
            if country is None:
                continue

            if "Electrolyzer" in asset_name:
                data["Electrolyzer"].loc[country, scen] += row.get("p_nom_opt", 0) or 0

            elif "H2 Turbine" in asset_name:
                data["H2 Turbine"].loc[country, scen] += row.get("p_nom_opt", 0) or 0

            elif "H2 Storage" in asset_name:
                data["H2 Storage"].loc[country, scen] += row.get("e_nom_opt", 0) or 0

    # Convert storage to GWh
    data["H2 Storage"] /= 1000

    # ---- Plot ----
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharex=True)
    fig.patch.set_facecolor(background_color)

    x = np.arange(len(countries))
    bar_width = 0.25

    scenario_colors = [colors[10], colors[14], colors[9]]

    panel_info = [
        ("Electrolyzer", "Electrolyzer [MW]"),
        ("H2 Turbine", "H2 turbine [MW]"),
        ("H2 Storage", "H2 storage [GWh]"),
    ]

    for ax, (tech, ylabel) in zip(axes, panel_info):
        ax.set_facecolor(background_color)

        for i, scen in enumerate(scenario_labels):
            values = data[tech][scen].values

            ax.bar(
                x + (i - 1) * bar_width,
                values,
                width=bar_width,
                label=scen,
                color=scenario_colors[i],
                edgecolor="white",
                linewidth=0.5,
            )

        ax.set_title(tech, fontweight="bold")
        ax.set_ylabel(ylabel)
        ax.set_xticks(x)
        ax.set_xticklabels(countries, rotation=30, ha="right")

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # Single legend (saves space)
    axes[0].legend(loc="upper left", frameon=True, facecolor="white")

    fig.suptitle(title, fontsize=13, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout()

    if save:
        fig_title = title.replace(" ", "_").lower()
        save_plot(fig_title)

    if show:
        plt.show()
        
def plot_dispatch(time_index, df, load, title, show=False, save=True,
                  power_axis_max=None, soc_axis_max=None):

    colors, background_color = color_palette()

    fig, ax1 = plt.subplots(figsize=(12, 4))
    fig.patch.set_facecolor(background_color)
    ax1.set_facecolor(background_color)

    ax2 = None

    components = [
        ("Coal Estonia", "Coal", colors[15]),
        ("OCGT Estonia", "Gas", colors[14]),
        ("Wind Generator Estonia", "Wind", colors[13]),
        ("Solar Generator Estonia", "Solar", colors[12]),
    ]

    if "Battery Discharge Estonia" in df.columns:
        components.append(("Battery Discharge Estonia", "Battery Discharge", colors[9]))

    # Check for H2 Turbine (generation source) - Estonia-only in the hourly dispatch plot
    h2_turbine_cols = [col for col in df.columns if "Estonia" in col and "H2 Turbine" in col]
    if h2_turbine_cols:
        # Aggregate all H2 turbine columns
        for col in h2_turbine_cols:
            components.append((col, "H2 Turbine", "#81C784"))

    stack_values = []
    stack_labels = []
    stack_colors = []

    for col, label, color in components:
        if col in df.columns:
            stack_values.append(np.asarray(df[col]))
            stack_labels.append(label)
            stack_colors.append(color)

    if len(stack_values) > 0:
        ax1.stackplot(
            time_index,
            *stack_values,
            labels=stack_labels,
            colors=stack_colors
        )

    load_values = np.asarray(load)
    ax1.plot(time_index, load_values, color="black", linewidth=2, label="Load [MW]")

    total_generation = np.sum(np.vstack(stack_values), axis=0) if len(stack_values) > 0 else np.zeros(len(time_index))

    # Battery charge as hatched area at top of generation stack
    if "Battery Charge Estonia" in df.columns and len(stack_values) > 0:
        charge_values = np.asarray(df["Battery Charge Estonia"])

        charging_mask = charge_values > 0
        if np.any(charging_mask):
            upper_bound = total_generation
            lower_bound = total_generation - charge_values

            ax1.fill_between(
                time_index,
                lower_bound,
                upper_bound,
                where=charging_mask,
                facecolor="none",
                edgecolor=colors[9],
                hatch="///",
                linewidth=0,
                label="Battery Charge [MW]",
                zorder=2.5,
            )

    # H2 Electrolyzer as hatched area below generation stack (consumption)
    electrolyzer_cols = [col for col in df.columns if "Estonia" in col and "Electrolyzer" in col]
    if electrolyzer_cols and len(stack_values) > 0:
        electrolyzer_power = np.zeros(len(time_index))
        for col in electrolyzer_cols:
            electrolyzer_power += np.asarray(df[col])
        
        charging_mask = electrolyzer_power > 0
        if np.any(charging_mask):
            upper_bound = total_generation
            lower_bound = total_generation - electrolyzer_power

            ax1.fill_between(
                time_index,
                lower_bound,
                upper_bound,
                where=charging_mask,
                facecolor="none",
                edgecolor="#FFA726",
                hatch="\\\\\\",
                linewidth=0,
                label="H2 Electrolyzer [MW]",
                zorder=2.5,
            )

    if "Battery SoC Estonia" in df.columns:
        ax2 = ax1.twinx()
        soc_values = np.asarray(df["Battery SoC Estonia"])

        ax2.step(
            time_index,
            soc_values,
            color=colors[1],
            linewidth=1.8,
            linestyle=":",
            label="Battery State of Charge [MWh]",
        )
        ax2.set_ylabel("State of Charge [MWh]")

        if soc_axis_max is not None:
            ax2.set_ylim(soc_axis_max * 1.1)
            
        ax2.spines["top"].set_visible(False)

    # H2 Storage SoC on secondary axis
    h2_storage_cols = [col for col in df.columns if "Estonia" in col and "H2 Storage SoC" in col]
    if h2_storage_cols:
        if ax2 is None:
            ax2 = ax1.twinx()
        
        h2_soc = np.zeros(len(time_index))
        for col in h2_storage_cols:
            h2_soc += np.asarray(df[col])
        
        ax2.step(
            time_index,
            h2_soc,
            color="#1976D2",
            linewidth=1.8,
            linestyle="--",
            label="H2 Storage SoC [MWh]",
        )
        ax2.set_ylabel("State of Charge [MWh]")

        if soc_axis_max is not None:
            ax2.set_ylim(soc_axis_max * 1.1)
            
        ax2.spines["top"].set_visible(False)

    ax1.set_xlabel("Time")
    ax1.set_ylabel("Power [MW]")

    if power_axis_max is not None:
        ax1.set_ylim(0, power_axis_max)
    else:
        ymax = max(np.max(total_generation), np.max(load_values)) * 1.1
        ax1.set_ylim(0, ymax)

    subtitle = "Wind, Solar, Gas, and Coal dispatch [MW]"
    if "Battery Discharge Estonia" in df.columns or "Battery SoC Estonia" in df.columns:
        subtitle = "Wind, Solar, Gas, Coal, and battery dispatch dynamics [MW/MWh]"
    if h2_turbine_cols or electrolyzer_cols:
        subtitle = "Wind, Solar, Gas, Coal, battery, and H2 dispatch dynamics [MW/MWh]"

    ax1.text(
        0.0, 1.07, title,
        transform=ax1.transAxes,
        fontsize=14,
        color="black",
        ha="left",
        fontweight="bold"
    )

    ax1.text(
        0.0, 1.01, subtitle,
        transform=ax1.transAxes,
        fontsize=10,
        color="black",
        ha="left"
    )

    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    lines_1, labels_1 = ax1.get_legend_handles_labels()
    if ax2 is not None:
        lines_2, labels_2 = ax2.get_legend_handles_labels()
    else:
        lines_2, labels_2 = [], []

    ax1.legend(
        lines_1 + lines_2,
        labels_1 + labels_2,
        bbox_to_anchor=(0.5, -0.18),
        ncol=4,
        loc="upper center",
        frameon=True,
        facecolor="white",
        framealpha=1,
    )

    fig.subplots_adjust(bottom=0.25)

    if save:
        fig_title = title.replace(" ", "_").lower()
        print("Saving:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()
        
def plot_dispatch_with_net_transmission(
    time_index, df, load, title, show=False, save=True,
    power_axis_max=None, soc_axis_max=None
):
    import numpy as np
    import matplotlib.pyplot as plt

    colors, background_color = color_palette()

    fig, ax1 = plt.subplots(figsize=(12, 4))
    fig.patch.set_facecolor(background_color)
    ax1.set_facecolor(background_color)

    ax2 = None

    components = [
        ("Coal Estonia", "Coal", colors[15]),
        ("OCGT Estonia", "Gas", colors[14]),
        ("Wind Generator Estonia", "Wind", colors[13]),
        ("Solar Generator Estonia", "Solar", colors[12]),
        
    ]

    if "Battery Discharge Estonia" in df.columns:
        components.append(("Battery Discharge Estonia", "Battery Discharge", colors[9]))

    stack_values = []
    stack_labels = []
    stack_colors = []

    for col, label, color in components:
        if col in df.columns:
            stack_values.append(np.asarray(df[col]))
            stack_labels.append(label)
            stack_colors.append(color)

    # Domestic generation stack
    if stack_values:
        ax1.stackplot(
            time_index,
            *stack_values,
            labels=stack_labels,
            colors=stack_colors
        )

    load_values = np.asarray(load)
    ax1.plot(time_index, load_values, color="black", linewidth=2, label="Load [MW]")

    domestic_generation = (
        np.sum(np.vstack(stack_values), axis=0)
        if stack_values else np.zeros(len(time_index))
    )

    # ---------------------------------
    # Net interchange for Estonia
    # positive => net import to Estonia
    # negative => net export from Estonia
    # ---------------------------------
    net_import_est = np.zeros(len(time_index))

    line_cols = [col for col in df.columns if "EST" in col and "-" in col]

    for col in line_cols:
        flow = np.asarray(df[col])
        left, right = col.split("-")

        if left == "EST":
            # positive flow means export from EST
            # so import to EST is negative of that
            net_import_est += -flow

        elif right == "EST":
            # positive flow means import to EST
            net_import_est += flow

    imports_est = np.clip(net_import_est, 0, None)
    exports_est = np.clip(-net_import_est, 0, None)

    # Full import band on top of domestic generation
    available_supply = domestic_generation + imports_est
    import_mask = imports_est > 0

    if np.any(import_mask):
        ax1.fill_between(
            time_index,
            domestic_generation,
            available_supply,
            where=import_mask,
            facecolor='none',
            edgecolor=colors[1],
            hatch='\\\\\\\\',
            linewidth=0,
            label="Net Import to Estonia [MW]",
            zorder=2.6,
        )

    # Battery charge as scrape from top
    available_after_charge = available_supply.copy()

    if "Battery Charge Estonia" in df.columns:
        charge_values = np.asarray(df["Battery Charge Estonia"])
        charging_mask = charge_values > 0

        if np.any(charging_mask):
            lower_bound = available_supply - charge_values
            upper_bound = available_supply

            ax1.fill_between(
                time_index,
                lower_bound,
                upper_bound,
                where=charging_mask,
                facecolor="none",
                edgecolor=colors[9],
                hatch="///",
                linewidth=0,
                label="Battery Charge [MW]",
                zorder=2.7,
            )

            available_after_charge = available_supply - charge_values

    # Net exports as scrape after charging
    export_mask = exports_est > 0
    if np.any(export_mask):
        lower_bound = available_after_charge - exports_est
        upper_bound = available_after_charge

        ax1.fill_between(
            time_index,
            lower_bound,
            upper_bound,
            where=export_mask,
            facecolor="none",
            edgecolor=colors[11],
            hatch="\\\\\\",
            linewidth=0,
            label="Net Export from Estonia [MW]",
            zorder=2.8,
        )

    # SoC on secondary axis
    if "Battery SoC Estonia" in df.columns:
        ax2 = ax1.twinx()
        soc_values = np.asarray(df["Battery SoC Estonia"])

        ax2.step(
            time_index,
            soc_values,
            color=colors[1],
            linewidth=1.8,
            linestyle=":",
            label="Battery State of Charge [MWh]",
        )
        ax2.set_ylabel("State of Charge [MWh]")

        if soc_axis_max is not None:
            ax2.set_ylim(soc_axis_max * 1.1)

        ax2.spines["top"].set_visible(False)

    ax1.set_xlabel("Time")
    ax1.set_ylabel("Power [MW]")

    if power_axis_max is not None:
        ax1.set_ylim(0, power_axis_max)
    else:
        ymax = max(
            np.max(available_supply) if len(available_supply) > 0 else 0,
            np.max(load_values)
        ) * 1.1
        ax1.set_ylim(0, ymax)

    subtitle = "Domestic dispatch, battery dynamics, and Estonia net imports/exports [MW/MWh]"

    ax1.text(
        0.0, 1.07,
        title,
        transform=ax1.transAxes,
        fontsize=14,
        color="black",
        ha="left",
        fontweight="bold"
    )

    ax1.text(
        0.0, 1.01,
        subtitle,
        transform=ax1.transAxes,
        fontsize=10,
        color="black",
        ha="left"
    )

    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    lines_1, labels_1 = ax1.get_legend_handles_labels()
    if ax2 is not None:
        lines_2, labels_2 = ax2.get_legend_handles_labels()
    else:
        lines_2, labels_2 = [], []

    ax1.legend(
        lines_1 + lines_2,
        labels_1 + labels_2,
        bbox_to_anchor=(0.5, -0.18),
        ncol=4,
        loc="upper center",
        frameon=True,
        facecolor="white",
        framealpha=1,
    )

    fig.subplots_adjust(bottom=0.28)

    if save:
        fig_title = title.replace(" ", "_").lower()
        print("Saving:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()

def plot_transmission_network(dispatch, load, title, show=False, save=True):
    """
    Plot a network graph showing transmission flows between countries.
    Node size = country total generation, edge width/color = net flow magnitude.
    """
    colors, background_color = color_palette()

    # Define interconnectors and their line colors
    interconnectors = [
        ("FIN-SWE", colors[0]),
        ("EST-FIN", colors[1]),
        ("EST-SWE", colors[2]),
        ("EST-LAT", colors[3]),
    ]

    # Create directed graph
    G = nx.DiGraph()
    countries = ["Estonia", "Finland", "Sweden", "Latvia"]
    G.add_nodes_from(countries)

    country_map = {
        "EST": "Estonia",
        "FIN": "Finland",
        "SWE": "Sweden",
        "LAT": "Latvia",
    }

    flows = {}
    for line, _ in interconnectors:
        if line in dispatch.columns:
            flows[line] = dispatch[line].sum()

    load_totals = {
        "Estonia": float(load["EE"].sum()) if isinstance(load, pd.DataFrame) and "EE" in load.columns else 0.0,
        "Finland": float(load["FI"].sum()) if isinstance(load, pd.DataFrame) and "FI" in load.columns else 0.0,
        "Sweden": float(load["SE"].sum()) if isinstance(load, pd.DataFrame) and "SE" in load.columns else 0.0,
        "Latvia": float(load["LV"].sum()) if isinstance(load, pd.DataFrame) and "LV" in load.columns else 0.0,
    }

    edge_labels = {}
    max_flow = max(abs(f) for f in flows.values()) if flows else 1.0

    for line, _ in interconnectors:
        if line not in flows:
            continue

        flow = flows[line]
        left_abbrev, right_abbrev = line.split("-")
        left = country_map[left_abbrev]
        right = country_map[right_abbrev]
        receiver = right if flow > 0 else left
        receiver_load = load_totals.get(receiver, 0.0)
        percent_of_load = (abs(flow) / receiver_load * 100.0) if receiver_load > 0 else 0.0

        if flow > 0:
            G.add_edge(left, right, flow=flow)
            edge_labels[(left, right)] = f"{abs(flow):.0f} MWh net exchange\n({percent_of_load:.1f}% of {receiver} annual load)"
        elif flow < 0:
            G.add_edge(right, left, flow=-flow)
            edge_labels[(right, left)] = f"{abs(flow):.0f} MWh net exchange\n({percent_of_load:.1f}% of {receiver} annual load)"

    # Layout and visualization
    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor(background_color)
    ax.set_facecolor(background_color)

    # Circular layout
    pos = nx.circular_layout(G, scale=2)

    # Draw nodes
    node_colors = [colors[13], colors[11], colors[13], colors[15]]
    nx.draw_networkx_nodes(
        G, pos,
        node_color=node_colors,
        node_size=3000,
        ax=ax,
        edgecolors="black",
        linewidths=2,
    )

    # Draw node labels
    nx.draw_networkx_labels(
        G, pos,
        font_size=11,
        font_weight="bold",
        font_color="white",
        ax=ax,
    )

    # Draw edges with width proportional to flow, using explicit arrow patches
    from matplotlib.patches import FancyArrowPatch

    edge_color_map = {
        ("Estonia", "Finland"): colors[1],
        ("Finland", "Estonia"): colors[1],
        ("Estonia", "Sweden"): colors[2],
        ("Sweden", "Estonia"): colors[2],
        ("Estonia", "Latvia"): colors[3],
        ("Latvia", "Estonia"): colors[3],
        ("Finland", "Sweden"): colors[0],
        ("Sweden", "Finland"): colors[0],
    }

    for (u, v), flow in nx.get_edge_attributes(G, "flow").items():
        width = max(1.0, 8 * flow / max_flow) if max_flow > 0 else 1.0
        edge_color = edge_color_map.get((u, v), colors[0])
        arrow = FancyArrowPatch(
            posA=pos[u],
            posB=pos[v],
            arrowstyle="-|>",
            mutation_scale=16 + 8 * (flow / max_flow if max_flow > 0 else 1.0),
            lw=width,
            color=edge_color,
            alpha=0.8,
            shrinkA=30,
            shrinkB=30,
            connectionstyle="arc3,rad=0.18",
        )
        ax.add_patch(arrow)

    # Draw edge labels (flow values)
    for (u_country, v_country), label in edge_labels.items():
        midpoint = (pos[u_country] + pos[v_country]) / 2
        direction = pos[v_country] - pos[u_country]
        norm = np.linalg.norm(direction)
        offset = np.array([0.0, 0.0])
        if norm > 0:
            offset = np.array([-direction[1], direction[0]]) / norm * 0.18

        x = midpoint[0] + offset[0]
        y = midpoint[1] + offset[1]
        ax.text(
            x, y, label,
            fontsize=8,
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", alpha=0.85),
        )

    ax.text(
        0.0, 1.07, title,
        transform=ax.transAxes,
        fontsize=14,
        color="black",
        ha="left",
        fontweight="bold"
    )

    ax.text(
        0.0, 1.01,
        "Annual net corridor exchange between countries (MWh). Percentages are relative to the receiving country's annual load, not traced supply.",
        transform=ax.transAxes,
        fontsize=10,
        color="black",
        ha="left"
    )

    ax.axis("off")

    if save:
        fig_title = title.replace(" ", "_").lower()
        print("Saving:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()

def plot_h2_transmission_network(dispatch, title, show=False, save=True):
    """
    Plot a network graph showing H2 transmission flows between countries.
    Node size and color represent presence of H2 infrastructure.
    Edge width/color = H2 pipeline flow magnitude.
    """
    colors, background_color = color_palette()

    # Define H2 pipeline interconnectors
    h2_pipelines = [
        ("FIN-SWE H2 Pipeline", "#87CEEB"),
        ("EST-FIN H2 Pipeline", "#4A90E2"),
        ("EST-SWE H2 Pipeline", "#357ABD"),
        ("EST-LAT H2 Pipeline", "#1E3A8A"),
    ]

    # Create directed graph
    G = nx.DiGraph()
    countries = ["Estonia", "Finland", "Sweden", "Latvia"]
    G.add_nodes_from(countries)

    country_map_h2 = {
        "EST": "Estonia",
        "FIN": "Finland",
        "SWE": "Sweden",
        "LAT": "Latvia",
    }

    flows = {}
    for pipeline, _ in h2_pipelines:
        if pipeline in dispatch.columns:
            flows[pipeline] = dispatch[pipeline].sum()

    edge_labels = {}
    max_flow = max(abs(f) for f in flows.values()) if flows else 1.0

    for pipeline, line_color in h2_pipelines:
        if pipeline not in flows:
            continue

        flow = flows[pipeline]
        # Extract country codes from pipeline name (e.g., "EST-FIN" from "EST-FIN H2 Pipeline")
        pipeline_name = pipeline.replace(" H2 Pipeline", "")
        parts = pipeline_name.split("-")
        if len(parts) == 2:
            left_abbrev, right_abbrev = parts
            left = country_map_h2.get(left_abbrev, left_abbrev)
            right = country_map_h2.get(right_abbrev, right_abbrev)

            if flow > 0:
                G.add_edge(left, right, flow=flow)
                edge_labels[(left, right)] = f"{abs(flow):.0f} MWh"
            elif flow < 0:
                G.add_edge(right, left, flow=-flow)
                edge_labels[(right, left)] = f"{abs(flow):.0f} MWh"

    # Layout and visualization
    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor(background_color)
    ax.set_facecolor(background_color)

    # Circular layout
    pos = nx.circular_layout(G, scale=2)

    # Draw nodes with light blue color for H2
    node_colors = ["#B3E5FC"] * len(countries)
    nx.draw_networkx_nodes(
        G, pos,
        node_color=node_colors,
        node_size=3000,
        ax=ax,
        edgecolors="#1976D2",
        linewidths=2,
    )

    # Draw node labels
    nx.draw_networkx_labels(
        G, pos,
        font_size=11,
        font_weight="bold",
        font_color="#01579B",
        ax=ax,
    )

    # Draw edges with width proportional to flow
    from matplotlib.patches import FancyArrowPatch

    edge_color_map_h2 = {
        ("Estonia", "Finland"): "#4A90E2",
        ("Finland", "Estonia"): "#4A90E2",
        ("Estonia", "Sweden"): "#357ABD",
        ("Sweden", "Estonia"): "#357ABD",
        ("Estonia", "Latvia"): "#1E3A8A",
        ("Latvia", "Estonia"): "#1E3A8A",
        ("Finland", "Sweden"): "#87CEEB",
        ("Sweden", "Finland"): "#87CEEB",
    }

    for (u, v), flow in nx.get_edge_attributes(G, "flow").items():
        width = max(1.0, 8 * flow / max_flow) if max_flow > 0 else 1.0
        edge_color = edge_color_map_h2.get((u, v), "#4A90E2")
        arrow = FancyArrowPatch(
            posA=pos[u],
            posB=pos[v],
            arrowstyle="-|>",
            mutation_scale=16 + 8 * (flow / max_flow if max_flow > 0 else 1.0),
            lw=width,
            color=edge_color,
            alpha=0.8,
            shrinkA=30,
            shrinkB=30,
            connectionstyle="arc3,rad=0.18",
        )
        ax.add_patch(arrow)

    # Draw edge labels (flow values)
    for (u_country, v_country), label in edge_labels.items():
        midpoint = (pos[u_country] + pos[v_country]) / 2
        direction = pos[v_country] - pos[u_country]
        norm = np.linalg.norm(direction)
        offset = np.array([0.0, 0.0])
        if norm > 0:
            offset = np.array([-direction[1], direction[0]]) / norm * 0.18

        x = midpoint[0] + offset[0]
        y = midpoint[1] + offset[1]
        ax.text(
            x, y, label,
            fontsize=8,
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", alpha=0.85),
        )

    ax.text(
        0.0, 1.07, title,
        transform=ax.transAxes,
        fontsize=14,
        color="black",
        ha="left",
        fontweight="bold"
    )

    ax.text(
        0.0, 1.01,
        "Annual net H2 transmission flows between countries (MWh)",
        transform=ax.transAxes,
        fontsize=10,
        color="black",
        ha="left"
    )

    ax.axis("off")

    if save:
        fig_title = title.replace(" ", "_").lower()
        print("Saving:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()

def plot_h2_dispatch(time_index, dispatch, title, show=False, save=True,
                     power_axis_max=None, soc_axis_max=None):
    """
    Plot hourly H2 system dispatch: electrolyzer consumption vs. turbine generation,
    with H2 storage state of charge on secondary axis.
    """
    colors, background_color = color_palette()

    fig, ax1 = plt.subplots(figsize=(12, 4))
    fig.patch.set_facecolor(background_color)
    ax1.set_facecolor(background_color)

    ax2 = None

    # Collect electrolyzer columns (sum across all countries)
    electrolyzer_cols = [col for col in dispatch.columns if "Electrolyzer" in col]
    turbine_cols = [col for col in dispatch.columns if "H2 Turbine" in col]
    storage_cols = [col for col in dispatch.columns if "H2 Storage" in col and "SoC" in col]

    # Sum electrolyzer consumption (negative, shown as consumption)
    electrolyzer_power = np.zeros(len(time_index))
    for col in electrolyzer_cols:
        if col in dispatch.columns:
            electrolyzer_power += np.asarray(dispatch[col])

    # Sum turbine generation (positive, shown as generation)
    turbine_power = np.zeros(len(time_index))
    for col in turbine_cols:
        if col in dispatch.columns:
            turbine_power += np.asarray(dispatch[col])

    # Sum H2 storage SoC
    storage_soc = np.zeros(len(time_index))
    for col in storage_cols:
        if col in dispatch.columns:
            storage_soc += np.asarray(dispatch[col])

    # Plot electrolyzer consumption as hatched area below zero
    electrolyzer_mask = electrolyzer_power > 0
    if np.any(electrolyzer_mask):
        ax1.fill_between(
            time_index,
            -electrolyzer_power,
            0,
            where=electrolyzer_mask,
            facecolor="#FFE082",
            edgecolor="#FFA726",
            linewidth=0.5,
            label="H2 Electrolyzer [MW]",
            alpha=0.8
        )

    # Plot turbine generation
    if np.any(turbine_power > 0):
        ax1.fill_between(
            time_index,
            0,
            turbine_power,
            facecolor="#81C784",
            edgecolor="#388E3C",
            linewidth=0.5,
            label="H2 Turbine [MW]",
            alpha=0.8
        )

    # Add H2 storage SoC on secondary axis
    if np.any(storage_soc > 0):
        ax2 = ax1.twinx()
        ax2.step(
            time_index,
            storage_soc,
            color="#1976D2",
            linewidth=2,
            label="H2 Storage SoC [MWh]",
        )
        ax2.set_ylabel("H2 Storage State of Charge [MWh]", fontsize=10)
        
        if soc_axis_max is not None:
            ax2.set_ylim(0, soc_axis_max * 1.1)
        
        ax2.spines["top"].set_visible(False)

    ax1.set_xlabel("Time")
    ax1.set_ylabel("Power [MW]")
    ax1.axhline(y=0, color="black", linewidth=1, linestyle="-", alpha=0.3)

    if power_axis_max is not None:
        ax1.set_ylim(-power_axis_max, power_axis_max)
    else:
        max_elec = np.max(electrolyzer_power) if np.any(electrolyzer_power) else 0
        max_turb = np.max(turbine_power) if np.any(turbine_power) else 0
        axis_max = max(max_elec, max_turb) * 1.1
        ax1.set_ylim(-axis_max, axis_max)

    ax1.text(
        0.0, 1.07, title,
        transform=ax1.transAxes,
        fontsize=14,
        color="black",
        ha="left",
        fontweight="bold"
    )

    ax1.text(
        0.0, 1.01, "H2 system dispatch: electrolyzer consumption (negative) vs. turbine generation (positive) [MW]",
        transform=ax1.transAxes,
        fontsize=10,
        color="black",
        ha="left"
    )

    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    lines_1, labels_1 = ax1.get_legend_handles_labels()
    if ax2 is not None:
        lines_2, labels_2 = ax2.get_legend_handles_labels()
    else:
        lines_2, labels_2 = [], []

    ax1.legend(
        lines_1 + lines_2,
        labels_1 + labels_2,
        bbox_to_anchor=(0.5, -0.18),
        ncol=3,
        loc="upper center",
        frameon=True,
        facecolor="white",
        framealpha=1,
    )

    fig.subplots_adjust(bottom=0.25)

    if save:
        fig_title = title.replace(" ", "_").lower()
        print("Saving:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()
        
def plot_heat_dispatch(time_index, df, heat_demand, node, title,
                       show=False, save=True, heat_axis_max=None):

    colors, background_color = color_palette()

    fig, ax1 = plt.subplots(figsize=(12, 4))
    fig.patch.set_facecolor(background_color)
    ax1.set_facecolor(background_color)

    heat_components = [
        (f"CHP {node} Heat", "CHP Heat", colors[15]),
        (f"Heat Pump {node}", "Heat Pump", colors[12]),
    ]

    stack_values = []
    stack_labels = []
    stack_colors = []

    for col, label, color in heat_components:
        if col in df.columns:
            stack_values.append(np.asarray(df[col]))
            stack_labels.append(label)
            stack_colors.append(color)

    if len(stack_values) > 0:
        ax1.stackplot(
            time_index,
            *stack_values,
            labels=stack_labels,
            colors=stack_colors
        )

    heat_demand_values = np.asarray(heat_demand)

    ax1.plot(
        time_index,
        heat_demand_values,
        color="black",
        linewidth=2,
        label="Heat demand [MW]"
    )

    total_heat_generation = (
        np.sum(np.vstack(stack_values), axis=0)
        if len(stack_values) > 0
        else np.zeros(len(time_index))
    )

    ax1.set_xlabel("Time")
    ax1.set_ylabel("Heat [MW]")

    if heat_axis_max is not None:
        ax1.set_ylim(0, heat_axis_max)
    else:
        ymax = max(np.max(total_heat_generation), np.max(heat_demand_values)) * 1.1
        ax1.set_ylim(0, ymax)

    ax1.text(
        0.0, 1.07, title,
        transform=ax1.transAxes,
        fontsize=14,
        color="black",
        ha="left",
        fontweight="bold"
    )

    ax1.text(
        0.0, 1.01, "CHP and heat pump heat dispatch [MW]",
        transform=ax1.transAxes,
        fontsize=10,
        color="black",
        ha="left"
    )

    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    lines_1, labels_1 = ax1.get_legend_handles_labels()

    ax1.legend(
        lines_1,
        labels_1,
        bbox_to_anchor=(0.5, -0.18),
        ncol=3,
        loc="upper center",
        frameon=True,
        facecolor="white",
        framealpha=1,
    )

    fig.subplots_adjust(bottom=0.25)

    if save:
        fig_title = title.replace(" ", "_").lower()
        print("Saving:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()
        


    colors, background_color = color_palette()

    countries = ["Estonia", "Finland", "Sweden", "Latvia"]

    technologies = [
        ("Nuclear", colors[8]),
        ("Coal", colors[15]),
        ("Gas", colors[14]),
        ("H2", colors[10]),
        ("Hydro", colors[11]),
        ("Wind", colors[13]),
        ("Solar", colors[12]),
        ("Battery", colors[9]),
        ("Heat Pump", colors[5]),
        ("CHP", colors[1])
    ]

    # If duplicate asset names exist, combine them
    capacities = capacities.groupby(capacities.index).sum(numeric_only=True)

    # Empty table: rows=countries, cols=technologies
    df_plot = pd.DataFrame(
        0.0,
        index=countries,
        columns=[tech for tech, _ in technologies]
    )

    # Iterate over asset rows
    for asset_name, row in capacities.iterrows():
        if not isinstance(asset_name, str):
            continue

        # Skip transmission lines/interconnectors
        if "-" in asset_name:
            continue

        # Find country
        country = None
        for c in countries:
            if asset_name.endswith(c):
                country = c
                break

        if country is None:
            continue

        # Choose the right capacity column
        p_nom = row["p_nom_opt"] if "p_nom_opt" in capacities.columns and pd.notna(row["p_nom_opt"]) else 0.0
        s_nom = row["s_nom_opt"] if "s_nom_opt" in capacities.columns and pd.notna(row["s_nom_opt"]) else 0.0

        # Classify technology
        if "Battery Storage" in asset_name:
            df_plot.loc[country, "Battery"] += p_nom
        elif "Electrolyzer" in asset_name or "H2 Turbine" in asset_name or "H2 Storage" in asset_name:
            df_plot.loc[country, "H2"] += p_nom
        elif "Wind" in asset_name:
            df_plot.loc[country, "Wind"] += p_nom
        elif "Solar" in asset_name:
            df_plot.loc[country, "Solar"] += p_nom
        elif "OCGT" in asset_name:
            df_plot.loc[country, "Gas"] += p_nom
        elif "Coal" in asset_name:
            df_plot.loc[country, "Coal"] += p_nom
        elif "Nuclear" in asset_name:
            df_plot.loc[country, "Nuclear"] += p_nom
        elif "Hydro" in asset_name:
            df_plot.loc[country, "Hydro"] += p_nom
        elif "Heat Pump" in asset_name:
            df_plot.loc[country, "Heat Pump"] += p_nom
        elif "CHP" in asset_name:
            df_plot.loc[country, "CHP"] += p_nom
        
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor(background_color)
    ax.set_facecolor(background_color)

    x = np.arange(len(countries))
    bottom = np.zeros(len(countries))
    plotted = False
    totals = df_plot.sum(axis=1).values

    inside_label_fraction = 0.08
    inside_label_min_abs = 120.0
    outside_x_offset = 0.18
    outside_label_min_gap = max(np.max(totals) * 0.02, 25.0) if len(totals) > 0 else 25.0
    outside_label_positions = {i: [] for i in range(len(countries))}

    for tech, color in technologies:
        values = df_plot[tech].values
        if np.all(values == 0):
            continue

        bars = ax.bar(
            x,
            values,
            bottom=bottom,
            label=tech,
            color=color,
            edgecolor="white",
            linewidth=0.5,
        )

        for i, (bar, value) in enumerate(zip(bars, values)):
            if value <= 0:
                continue

            y_center = bottom[i] + value / 2
            inside_threshold = max(inside_label_min_abs, inside_label_fraction * totals[i])

            if value >= inside_threshold:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    y_center,
                    f"{value:.0f}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color=_contrast_text_color(color),

                )
            else:
                y_text = y_center
                while any(abs(y_text - y_used) < outside_label_min_gap for y_used in outside_label_positions[i]):
                    y_text += outside_label_min_gap
                outside_label_positions[i].append(y_text)

                x_center = bar.get_x() + bar.get_width() / 2
                x_right = bar.get_x() + bar.get_width()

                ax.annotate(
                    f"{value:.0f}",
                    xy=(x_right, y_center),
                    xytext=(x_center + outside_x_offset, y_text),
                    ha="left",
                    va="center",
                    fontsize=8,
                    color=_contrast_text_color(color),
                    arrowprops=dict(
                        arrowstyle="-",
                        color=_contrast_text_color(color),
                        linewidth=0.6,
                        shrinkA=0,
                        shrinkB=0,
                    ),
                )

        bottom += values
        plotted = True

    ax.set_xticks(x)
    ax.set_xticklabels(countries)
    ax.set_ylabel("Installed capacity [MW]")
    ax.set_xlim(-0.5, len(countries) - 0.5 + 0.3)

    ax.text(
        0.0, 1.07,
        title,
        transform=ax.transAxes,
        fontsize=14,
        color="black",
        ha="left",
        fontweight="bold",
    )

    ax.text(
        0.0, 1.01,
        "Installed generator and storage capacity by country [MW]",
        transform=ax.transAxes,
        fontsize=10,
        color="black",
        ha="left",
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    if plotted:
        ax.legend(
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),  # move to right side
            ncol=1,  # vertical legend looks cleaner here
            frameon=True,
            facecolor="white",
            framealpha=1,
        )

    # Make room for legend on the right
    fig.subplots_adjust(right=0.8)
    
    
    if save:
        fig_title = title.replace(" ", "_").lower()
        print("Saving:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()