"""
03_make_charts.py
=================
Builds the four charts used in the README from data/energy.db.
Each chart answers one of the business questions; the SQL behind it is the
matching query in sql/analysis.sql.

Output:
    outputs/charts/01_price_vs_renewables.svg
    outputs/charts/02_daily_price_profile.svg
    outputs/charts/03_merit_order.svg
    outputs/charts/04_negative_hours.svg

Run:  python src/03_make_charts.py
"""

import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "energy.db"
OUT = ROOT / "outputs" / "charts"

BLUE = "#2f6db5"
ORANGE = "#e08a1e"
GREEN = "#3a9a5b"
GREY = "#6b7280"
SEASON_COLORS = {"Winter": BLUE, "Spring": GREEN, "Summer": ORANGE, "Autumn": "#9c5b2e"}

plt.rcParams.update({
    "font.size": 10, "svg.fonttype": "none", "svg.hashsalt": "smard",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "axes.titlesize": 12, "axes.titlelocation": "left",
})


def query(con, sql):
    return pd.read_sql(sql, con)


def source_note(fig, extra=""):
    text = "Source: Bundesnetzagentur | SMARD.de (CC BY 4.0)" + (f". {extra}" if extra else "")
    fig.text(0.01, 0.01, text, fontsize=8, color=GREY)


def chart_price_vs_renewables(con):
    df = query(con, """
        SELECT year,
               AVG(price_eur_mwh) AS price,
               100.0 * SUM(renewable_mwh) / SUM(generation_mwh) AS renewable_share
        FROM hourly GROUP BY year ORDER BY year""")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    bars = ax.bar(df["year"].astype(str), df["price"], color=BLUE, width=0.6)
    bars[-1].set_alpha(0.55)  # current year is not complete
    ax.bar_label(bars, fmt="%.0f", padding=2, fontsize=9)
    ax.set_ylabel("Average day-ahead price (EUR/MWh)")
    ax2 = ax.twinx()
    ax2.plot(df["year"].astype(str), df["renewable_share"], color=GREEN, marker="o", linewidth=2)
    ax.set_ylim(0, 270)
    ax2.set_ylim(0, 75)
    ax2.set_ylabel("Renewable share of generation (%)", color=GREEN)
    ax2.spines["top"].set_visible(False)
    ax.set_title("Renewables up since 2021; prices peaked in the 2022 gas crisis")
    source_note(fig, f"{df['year'].max()} is year to date")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "01_price_vs_renewables.svg")
    plt.close(fig)


def chart_daily_profile(con):
    df = query(con, """
        SELECT season, hour, AVG(price_eur_mwh) AS price
        FROM hourly WHERE year >= 2023
        GROUP BY season, hour""")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for season in ["Winter", "Spring", "Summer", "Autumn"]:
        s = df[df["season"] == season]
        ax.plot(s["hour"], s["price"], label=season, color=SEASON_COLORS[season], linewidth=2)
    ax.set_xticks(range(0, 24, 3))
    ax.set_xlabel("Hour of day (German local time)")
    ax.set_ylabel("Average price (EUR/MWh)")
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, ncol=4, loc="upper left")
    ax.set_title("Solar creates a midday price dip in spring and summer")
    source_note(fig, "2023 to date")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "02_daily_price_profile.svg")
    plt.close(fig)


def chart_merit_order(con):
    df = query(con, """
        SELECT CAST(renewable_share * 10 AS INT) * 10 AS band,
               COUNT(*) AS hours,
               AVG(price_eur_mwh) AS price,
               100.0 * AVG(is_negative_price) AS pct_negative
        FROM hourly
        WHERE year >= 2023 AND renewable_share IS NOT NULL
        GROUP BY band ORDER BY band""")
    labels = [f"{b}-{b + 10}%" for b in df["band"]]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    colors = [GREEN if p < 0 else BLUE for p in df["price"]]
    bars = ax.bar(labels, df["price"], color=colors, width=0.65)
    ax.bar_label(bars, fmt="%.0f", padding=2, fontsize=9)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylim(df["price"].min() - 25, df["price"].max() + 20)
    ax.set_xlabel("Share of generation from renewables in that hour")
    ax.set_ylabel("Average price (EUR/MWh)")
    ax.set_title("The more renewables in an hour, the cheaper the power")
    source_note(fig, "2023 to date, hourly")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "03_merit_order.svg")
    plt.close(fig)


def chart_negative_hours(con):
    df = query(con, """
        SELECT year, hour, SUM(is_negative_price) AS n
        FROM hourly GROUP BY year, hour""")
    grid = df.pivot(index="year", columns="hour", values="n").fillna(0)
    fig, ax = plt.subplots(figsize=(9, 3.8))
    im = ax.imshow(grid.values, aspect="auto", cmap="Greens")
    ax.set_xticks(range(0, 24, 2))
    ax.set_yticks(range(len(grid.index)))
    ax.set_yticklabels(grid.index)
    ax.set_xlabel("Hour of day (German local time)")
    for spine in ax.spines.values():
        spine.set_visible(False)
    cbar = fig.colorbar(im, ax=ax, pad=0.01)
    cbar.set_label("Hours with a negative price")
    ax.set_title("Negative prices are now concentrated in sunny middays")
    source_note(fig, f"{grid.index.max()} is year to date")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "04_negative_hours.svg")
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as con:
        chart_price_vs_renewables(con)
        chart_daily_profile(con)
        chart_merit_order(con)
        chart_negative_hours(con)
    print(f"Charts saved to {OUT}")


if __name__ == "__main__":
    main()
