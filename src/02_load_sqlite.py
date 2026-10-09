"""
02_load_sqlite.py
=================
Loads data/raw/smard_hourly.csv into a SQLite database and adds the columns
every analysis needs, so the SQL stays simple.

Added columns:
    date, year, month, hour, weekday (1=Mon..7=Sun), season    local German time
    renewable_mwh        solar + wind onshore + wind offshore + biomass + hydro + other renewables
    fossil_mwh           lignite + hard coal + natural gas + other conventional
    generation_mwh       all generation types (incl. nuclear and pumped storage)
    renewable_share      renewable_mwh / generation_mwh
    is_negative_price    1 if the day-ahead price is below 0

Output:
    data/energy.db                      table `hourly`
    data/processed/hourly_powerbi.csv   same data for Power BI (local time, no timezone suffix)

Run:  python src/02_load_sqlite.py
"""

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "raw" / "smard_hourly.csv"
DB = ROOT / "data" / "energy.db"
PBI = ROOT / "data" / "processed" / "hourly_powerbi.csv"

RENEWABLE = ["solar_mwh", "wind_onshore_mwh", "wind_offshore_mwh", "biomass_mwh",
             "hydro_mwh", "other_renewables_mwh"]
FOSSIL = ["lignite_mwh", "hard_coal_mwh", "natural_gas_mwh", "other_conventional_mwh"]
OTHER_GEN = ["nuclear_mwh", "pumped_storage_mwh"]
SEASON = {12: "Winter", 1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring", 5: "Spring",
          6: "Summer", 7: "Summer", 8: "Summer", 9: "Autumn", 10: "Autumn", 11: "Autumn"}


def enrich(df):
    ts = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert("Europe/Berlin")
    df["local_time"] = ts.dt.strftime("%Y-%m-%d %H:%M")
    df["date"] = ts.dt.strftime("%Y-%m-%d")
    df["year"] = ts.dt.year
    df["month"] = ts.dt.month
    df["hour"] = ts.dt.hour
    df["weekday"] = ts.dt.dayofweek + 1
    df["season"] = df["month"].map(SEASON)
    df["renewable_mwh"] = df[RENEWABLE].sum(axis=1, min_count=1)
    df["fossil_mwh"] = df[FOSSIL].sum(axis=1, min_count=1)
    df["generation_mwh"] = df[RENEWABLE + FOSSIL + OTHER_GEN].sum(axis=1, min_count=1)
    df["renewable_share"] = (df["renewable_mwh"] / df["generation_mwh"]).round(4)
    df["is_negative_price"] = (df["price_eur_mwh"] < 0).astype(int)
    return df


def main():
    df = enrich(pd.read_csv(CSV))
    with sqlite3.connect(DB) as con:
        df.to_sql("hourly", con, if_exists="replace", index=False)
        con.execute("CREATE INDEX IF NOT EXISTS ix_hourly_date ON hourly(date)")
        n = con.execute("SELECT COUNT(*) FROM hourly").fetchone()[0]
    print(f"Loaded {n:,} rows into {DB} (table: hourly)")
    PBI.parent.mkdir(parents=True, exist_ok=True)
    df.drop(columns=["timestamp"]).to_csv(PBI, index=False)
    print(f"Wrote {PBI} for Power BI")


if __name__ == "__main__":
    main()
