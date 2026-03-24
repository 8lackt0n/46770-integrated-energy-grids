import matplotlib.pyplot as plt
import os
import numpy as np


def _dispatch_series(df):
    colors, _ = color_palette()
    series = [
        ("Wind Generator Estonia", "Wind Production [MWh]", colors[13]),
        ("Solar Generator Estonia", "PV Production [MWh]", colors[12]),
        ("OCGT Estonia", "Gas Production [MWh]", colors[14]),
        ("Coal Estonia", "Coal Production [MWh]", colors[15]),
    ]

    if "Battery Storage Discharge" in df.columns:
        series.append(("Battery Storage Discharge", "Battery Discharge [MWh]", colors[9]))

    return series


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


def save_plot(file_name):
    os.makedirs("plots", exist_ok=True)
    output_path = os.path.join("plots", f"{file_name}.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')


def plot_dispatch(time_index, df, load, title, show=False, save=True):
    colors, background_color = color_palette()

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(background_color)
    ax.set_facecolor(background_color)

    ax.set_xlabel("Time")
    ax.text(0.0, 1.07, title, transform=ax.transAxes, fontsize=14,
            color="black", ha="left", fontweight="bold")
    subtitle = "Wind, Solar, Gas, and Coal Production in MWh"
    if "Battery Storage Discharge" in df.columns:
        subtitle = "Wind, Solar, Gas, Coal, and Battery Discharge in MWh"

    ax.text(0.0, 1.03, subtitle,
            transform=ax.transAxes, fontsize=10, color="black", ha="left")

    ax.legend(bbox_to_anchor=(0.5, -0.10), ncol=4, loc="upper center")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    dispatch_series = _dispatch_series(df)
    stack_values = [df[col] for col, _, _ in dispatch_series]
    stack_labels = [label for _, label, _ in dispatch_series]
    stack_colors = [color for _, _, color in dispatch_series]

    ax.stackplot(time_index,
                 *stack_values,
                 labels=stack_labels,
                 colors=stack_colors)

    total_generation = np.sum(np.vstack([np.asarray(values) for values in stack_values]), axis=0)
    load_values = np.asarray(load)
    charging_mask = total_generation > load_values

    if np.any(charging_mask):
        ax.fill_between(
            time_index,
            load_values,
            total_generation,
            where=charging_mask,
            facecolor="none",
            edgecolor=colors[9],
            hatch="///",
            linewidth=0,
            label="Battery Charge (MWh)",
            zorder=2.5,
        )

    ax.plot(time_index, load, label='Load [MWh]', color='black', linewidth=2)
    ax.set_xlabel('Time')
    ax.text(0.0, 1.07, title, transform=ax.transAxes, fontsize=14, color='black', ha='left', fontweight='bold')
    ax.text(0.0, 1.03, subtitle, transform=ax.transAxes, fontsize=10, color='black', ha='left')
    ax.legend(bbox_to_anchor=(0.5, -0.10), ncol=4, loc='upper center')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    if save:
        fig_title = title.replace(" ", "_").lower()
        print("About to save:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()
    #plt.close(fig)


def plot_annual_energy_mix(df, title, show=False, save=True):
    colors, background_color = color_palette()

    components = [
        ("Wind Generator Estonia", "Wind", colors[13]),
        ("Solar Generator Estonia", "Solar", colors[12]),
        ("OCGT Estonia", "Gas", colors[14]),
        ("Coal Estonia", "Coal", colors[15]),
    ]
    if "Battery Storage Discharge" in df.columns:
        components.append(("Battery Storage Discharge", "Battery Discharge", colors[9]))
    

    values = [df[col].sum() for col, _, _ in components]
    labels = [label for _, label, _ in components]
    pie_colors = [color for _, _, color in components]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(background_color)
    ax.set_facecolor(background_color)
    ax.pie(values, labels=labels, colors=pie_colors, autopct='%1.1f%%')
    ax.text(0.0, 1.07, title, transform=ax.transAxes, fontsize=14, color='black', ha='left', fontweight='bold')
    annual_subtitle = 'Total Wind, Solar, Gas, and Coal Production in MWh'
    if "Battery Storage Discharge" in df.columns:
        annual_subtitle = 'Total Wind, Solar, Gas, Coal, and Battery Discharge in MWh'

    ax.text(0.0, 1.03, annual_subtitle, transform=ax.transAxes, fontsize=10, color='black', ha='left')
    ax.legend(bbox_to_anchor=(0.5, -0.10), ncol=4, loc='upper center')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    if save:
        fig_title = title.replace(" ", "_").lower()
        print("About to save:", fig_title)
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
    if "Battery Storage Discharge" in df.columns:
        series.append(("Battery Storage Discharge", "Battery Discharge", colors[9]))

    hours = range(len(df))

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(background_color)
    ax.set_facecolor(background_color)

    for col, label, color in series:
        sorted_values = df[col].sort_values(ascending=False).reset_index(drop=True)
        ax.plot(hours, sorted_values, label=label, color=color)

    ax.set_xlabel("Hours (sorted)")
    ax.set_ylabel("Generation [MWh]")

    ax.text(0.0, 1.07,
        title,
        transform=ax.transAxes,
        fontsize=14,
        fontweight="bold"
    )

    ax.text(0.0, 1.03,
        "Sorted hourly generation for each technology",
        transform=ax.transAxes,
        fontsize=10
    )

    ax.legend(bbox_to_anchor=(0.5, -0.10), ncol=4, loc="upper center")

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    if save:
        fig_title = title.replace(" ", "_").lower()
        print("About to save:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()

def plot_capacity_variability(capacity_df, title, show=False, save=True):

    colors, background_color = color_palette()

    avg = capacity_df.mean()
    std = capacity_df.std()

    fig, ax = plt.subplots(figsize=(10,6))
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

    ax.text(0.0, 1.03,
        "Error bars show standard deviation across weather years",
        transform=ax.transAxes,
        fontsize=10
    )

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    if save:
        fig_title = title.replace(" ", "_").lower()
        print("About to save:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()


def plot_storage_operation(time_index, storage_df, title, show=False, save=True):
    colors, background_color = color_palette()

    fig, ax1 = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(background_color)
    ax1.set_facecolor(background_color)

    ax1.step(
        time_index,
        storage_df["Battery Storage Discharge"],
        label="Battery Discharge [MWh]",
        color=colors[9],
    )
    ax1.step(
        time_index,
        storage_df["Battery Storage Charge"],
        label="Battery Charge [MWh]",
        color=colors[1],
    )
    ax1.set_ylabel("Power [MW]")

    ax2 = ax1.twinx()
    ax2.plot(
        time_index,
        storage_df["Battery Storage SoC"],
        label="Battery State of Charge [MWh]",
        color="black",
        linewidth=2,
    )
    ax2.set_ylabel("State of Charge [MWh]")

    ax1.text(0.0, 1.07, title, transform=ax1.transAxes, fontsize=14, color="black", ha="left", fontweight="bold")
    ax1.text(0.0, 1.03, "Battery charging, discharging, and state of charge", transform=ax1.transAxes, fontsize=10, color="black", ha="left")

    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(lines_1 + lines_2, labels_1 + labels_2, bbox_to_anchor=(0.5, -0.10), ncol=3, loc="upper center")

    ax1.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)

    if save:
        fig_title = title.replace(" ", "_").lower()
        print("About to save:", fig_title)
        save_plot(fig_title)

    if show:
        plt.show()

