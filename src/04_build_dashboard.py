"""
04_build_dashboard.py
=====================
Builds an interactive, self-contained HTML dashboard from data/energy.db.

The script aggregates the hourly table into small summary tables
(year x month, year x season x hour, year x season x renewable-share band)
plus day-level figures (price spread, peak, top 10 days) per year and season,
embeds them as JSON, and writes one HTML file. All filtering and charting
happens in the browser with plain JavaScript and SVG, so the file works offline
and on GitHub (via htmlpreview) without any server or library.

Output:
    outputs/dashboard.html

Run:  python src/04_build_dashboard.py
"""

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "energy.db"
OUT = ROOT / "outputs" / "dashboard.html"
TEMPLATE = ROOT / "src" / "dashboard_template.html"

# Only hours where every series is available, so all numbers use the same hours.
COMPLETE = "load_mwh IS NOT NULL AND price_eur_mwh IS NOT NULL"

MONTHLY_SQL = f"""
    SELECT month,
           COUNT(*), SUM(price_eur_mwh),
           SUM(renewable_mwh), SUM(generation_mwh),
           SUM(wind_onshore_mwh + wind_offshore_mwh), SUM(solar_mwh),
           SUM(biomass_mwh + hydro_mwh + other_renewables_mwh),
           SUM(natural_gas_mwh), SUM(lignite_mwh + hard_coal_mwh),
           SUM(nuclear_mwh + pumped_storage_mwh + other_conventional_mwh),
           SUM(is_negative_price)
    FROM hourly WHERE {COMPLETE} AND {{where}}
    GROUP BY month
"""

HOURLY_SQL = f"""
    SELECT season, hour, COUNT(*), SUM(price_eur_mwh), SUM(is_negative_price)
    FROM hourly WHERE {COMPLETE} AND {{where}}
    GROUP BY season, hour
"""

BANDS_SQL = f"""
    SELECT season, MIN(CAST(renewable_share * 10 AS INT), 9) AS band,
           COUNT(*), SUM(price_eur_mwh), SUM(is_negative_price)
    FROM hourly WHERE {COMPLETE} AND renewable_share IS NOT NULL AND {{where}}
    GROUP BY season, band
"""

DAILY_SQL = f"""
    SELECT date, MAX(price_eur_mwh), MIN(price_eur_mwh), AVG(price_eur_mwh),
           AVG(wind_onshore_mwh + wind_offshore_mwh) / 1000,
           SUM(renewable_mwh) / SUM(generation_mwh)
    FROM hourly WHERE {COMPLETE} AND {{where}}
    GROUP BY date ORDER BY date
"""

SEASONS = {"All": None, "Winter": (12, 1, 2), "Spring": (3, 4, 5),
           "Summer": (6, 7, 8), "Autumn": (9, 10, 11)}


def day_summary(days):
    """Daily figures for one period: average daily spread (max - min), highest hourly
    price, average wind, and the 10 days with the highest average price."""
    top = sorted(days, key=lambda d: d[3], reverse=True)[:10]
    return {
        "spread": round(sum(d[1] - d[2] for d in days) / len(days), 1),
        "max": round(max(d[1] for d in days), 1),
        "wind": round(sum(d[4] for d in days) / len(days), 1),
        "top": [[d[0], round(d[3], 1), round(d[1], 1), round(d[4], 1), round(d[5], 3)] for d in top],
    }


def periods(con):
    """Every full year, plus the previous year cut at the same day as the latest data,
    so the latest (incomplete) year can be compared like for like."""
    last = con.execute(f"SELECT MAX(date) FROM hourly WHERE {COMPLETE}").fetchone()[0]
    years = [r[0] for r in con.execute("SELECT DISTINCT year FROM hourly ORDER BY year")]
    latest = years[-1]
    out = {str(y): f"year = {y}" for y in years}
    if latest - 1 in years:
        cutoff = f"{latest - 1}{last[4:]}"
        out[f"{latest - 1}ytd"] = f"year = {latest - 1} AND date <= '{cutoff}'"
    return out, years, last


def build_data(con):
    keys, years, last = periods(con)
    monthly, hourly, bands, daily = [], [], [], {}
    all_years = " OR ".join(f"({keys[str(y)]})" for y in years)
    for key, where in list(keys.items()) + [("All", all_years)]:
        days = con.execute(DAILY_SQL.format(where=f"({where})")).fetchall()
        daily[key] = {}
        for season, months in SEASONS.items():
            subset = [d for d in days if months is None or int(d[0][5:7]) in months]
            if subset:
                daily[key][season] = day_summary(subset)
        if key == "All":
            continue
        for row in con.execute(MONTHLY_SQL.format(where=where)):
            monthly.append([key] + [round(v) for v in row])
        for row in con.execute(HOURLY_SQL.format(where=where)):
            hourly.append([key, row[0]] + [round(v) for v in row[1:]])
        for row in con.execute(BANDS_SQL.format(where=where)):
            bands.append([key, row[0]] + [round(v) for v in row[1:]])
    first = con.execute(f"SELECT MIN(date) FROM hourly WHERE {COMPLETE}").fetchone()[0]
    n_days = con.execute(f"SELECT COUNT(DISTINCT date) FROM hourly WHERE {COMPLETE}").fetchone()[0]
    return {
        "meta": {"first": first, "last": last, "days": n_days, "years": years,
                 "ytdKey": f"{years[-1] - 1}ytd"},
        "monthly": monthly,
        "hourly": hourly,
        "bands": bands,
        "daily": daily,
    }


def main():
    with sqlite3.connect(DB) as con:
        data = build_data(con)
    html = TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"Dashboard written to {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
