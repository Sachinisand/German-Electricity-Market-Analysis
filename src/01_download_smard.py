"""
01_download_smard.py
====================
Downloads hourly German electricity market data from SMARD (Bundesnetzagentur,
https://www.smard.de) and saves it as one tidy CSV.

SMARD serves each series as weekly JSON files:
    index:  /app/chart_data/{id}/{region}/index_hour.json        -> list of week start timestamps
    week:   /app/chart_data/{id}/{region}/{id}_{region}_hour_{ts}.json  -> [[timestamp_ms, value], ...]

Units: generation and load in MWh per hour (= average MW), price in EUR/MWh.
Data licence: CC BY 4.0, source "Bundesnetzagentur | SMARD.de".

Output:
    data/raw/smard_hourly.csv   one row per hour (Europe/Berlin time), one column per series

Run:  python src/01_download_smard.py --start 2019-01-01
"""

import argparse
import json
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"
RAW = ROOT / "data" / "raw"
BASE = "https://www.smard.de/app/chart_data"

# SMARD filter id -> (column name, region). The price is published for the
# DE-LU bidding zone; everything else for Germany.
SERIES = {
    4169: ("price_eur_mwh", "DE-LU"),
    410: ("load_mwh", "DE"),
    4359: ("residual_load_mwh", "DE"),
    4068: ("solar_mwh", "DE"),
    4067: ("wind_onshore_mwh", "DE"),
    1225: ("wind_offshore_mwh", "DE"),
    4066: ("biomass_mwh", "DE"),
    1226: ("hydro_mwh", "DE"),
    1228: ("other_renewables_mwh", "DE"),
    1223: ("lignite_mwh", "DE"),
    4069: ("hard_coal_mwh", "DE"),
    4071: ("natural_gas_mwh", "DE"),
    1224: ("nuclear_mwh", "DE"),
    4070: ("pumped_storage_mwh", "DE"),
    1227: ("other_conventional_mwh", "DE"),
}


def get_json(url, session, retries=3):
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))


def week_file(series_id, region, ts, session):
    """Return one weekly file, using a local cache so re-runs are fast and polite."""
    path = CACHE / f"{series_id}_{region}_{ts}.json"
    if path.exists():
        return json.loads(path.read_text())
    data = get_json(f"{BASE}/{series_id}/{region}/{series_id}_{region}_hour_{ts}.json", session)
    # Only cache complete past weeks; the current week is still being filled.
    if all(v is not None for _, v in data["series"]):
        path.write_text(json.dumps(data))
    return data


def download_series(series_id, region, start_ms, session):
    index = get_json(f"{BASE}/{series_id}/{region}/index_hour.json", session)
    weeks = [ts for ts in index["timestamps"] if ts >= start_ms - 7 * 24 * 3600 * 1000]
    points = []
    for ts in weeks:
        points.extend(week_file(series_id, region, ts, session)["series"])
        time.sleep(0.05)
    return points


def to_frame(points, column):
    df = pd.DataFrame(points, columns=["ts_ms", column]).dropna()
    return df.drop_duplicates("ts_ms").set_index("ts_ms")


def build_table(frames, start):
    df = pd.concat(frames, axis=1).sort_index()
    df.index = (pd.to_datetime(df.index, unit="ms", utc=True)
                  .tz_convert("Europe/Berlin").rename("timestamp"))
    df = df[df.index >= pd.Timestamp(start, tz="Europe/Berlin")]
    # Nuclear stopped in April 2023 and SMARD ends the series later; treat missing as 0.
    if "nuclear_mwh" in df:
        df["nuclear_mwh"] = df["nuclear_mwh"].fillna(0)
    return df


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2019-01-01", help="first day to keep (YYYY-MM-DD)")
    args = p.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    start_ms = int(pd.Timestamp(args.start, tz="Europe/Berlin").timestamp() * 1000)

    frames = []
    with requests.Session() as session:
        for series_id, (column, region) in SERIES.items():
            print(f"Downloading {column} ...", flush=True)
            frames.append(to_frame(download_series(series_id, region, start_ms, session), column))

    df = build_table(frames, args.start)
    out = RAW / "smard_hourly.csv"
    df.to_csv(out)
    print(f"Saved {len(df):,} hours x {df.shape[1]} series to {out}")
    missing = df.isna().sum()
    missing = missing[missing > 0]
    print("Missing values per column:", "none" if missing.empty else "\n" + missing.to_string())


if __name__ == "__main__":
    main()
