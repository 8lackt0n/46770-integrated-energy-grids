import matplotlib.pyplot as plt
import os


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
        "#2A9D8F",
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

    ax.step(time_index, df["Wind Generator"], label="Wind Production [MWh]", color=colors[13])
    ax.step(time_index, df["Solar Generator"], label="PV Production [MWh]", color=colors[12])
    ax.step(time_index, df["OCGT"], label="Gas Production [MWh]", color=colors[14])
    ax.step(time_index, df["Coal"], label="Coal Production [MWh]", color=colors[15])

    ax.set_xlabel("Time")
    ax.text(0.0, 1.07, title, transform=ax.transAxes, fontsize=14,
            color="black", ha="left", fontweight="bold")
    ax.text(0.0, 1.03, "Wind, Solar, Gas, and Coal Production in MWh",
            transform=ax.transAxes, fontsize=10, color="black", ha="left")

    ax.legend(bbox_to_anchor=(0.5, -0.10), ncol=4, loc="upper center")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.stackplot(time_index, 
                 df['Wind Generator'], 
                 df['Solar Generator'], 
                 df['OCGT'], 
                 df['Coal'],
                 labels=['Wind Production [MWh]', 'PV Production [MWh]', 'Gas Production [MWh]', 'Coal Production [MWh]'],
                 colors=[colors[13], colors[12], colors[14], colors[15]])
    ax.plot(time_index, load, label='Load [MWh]', color='black', linewidth=2)
    ax.set_xlabel('Time')
    ax.text(0.0, 1.07, title, transform=ax.transAxes, fontsize=14, color='black', ha='left', fontweight='bold')
    ax.text(0.0, 1.03, 'Wind, Solar, Gas, and Coal Production in MWh', transform=ax.transAxes, fontsize=10, color='black', ha='left')
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

    tot_wind = sum(df["Wind Generator"])
    tot_solar = sum(df["Solar Generator"])
    tot_gas = sum(df["OCGT"])
    tot_coal = sum(df["Coal"])
    
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(background_color)
    ax.set_facecolor(background_color)
    ax.pie([tot_wind, tot_solar, tot_gas, tot_coal], labels=['Wind', 'Solar', 'Gas', 'Coal'], colors=[colors[13], colors[12], colors[14], colors[15]], autopct='%1.1f%%')
    ax.text(0.0, 1.07, title, transform=ax.transAxes, fontsize=14, color='black', ha='left', fontweight='bold')
    ax.text(0.0, 1.03, 'Total Wind, Solar, Gas, and Coal Production in MWh', transform=ax.transAxes, fontsize=10, color='black', ha='left')
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

    wind_sorted = df["Wind Generator"].sort_values(ascending=False).reset_index(drop=True)
    solar_sorted = df["Solar Generator"].sort_values(ascending=False).reset_index(drop=True)
    gas_sorted = df["OCGT"].sort_values(ascending=False).reset_index(drop=True)
    coal_sorted = df["Coal"].sort_values(ascending=False).reset_index(drop=True)

    hours = range(len(df))

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(background_color)
    ax.set_facecolor(background_color)

    ax.plot(hours, wind_sorted, label="Wind", color=colors[13])
    ax.plot(hours, solar_sorted, label="Solar", color=colors[12])
    ax.plot(hours, gas_sorted, label="Gas", color=colors[14])
    ax.plot(hours, coal_sorted, label="Coal", color=colors[15])

    ax.set_xlabel("Hours (sorted)")
    ax.set_ylabel("Generation [MWh]")

    ax.text(0.0, 1.07,
        "Generation Duration Curve",
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

