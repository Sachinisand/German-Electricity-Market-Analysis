# German Electricity Market Analysis

**How does the growth of wind and solar change electricity prices in Germany, and what does that mean for companies that buy or sell power?**

Hourly day-ahead prices, electricity consumption and generation by source from **SMARD** (Bundesnetzagentur), analysed with Python, SQL and Power BI.

> **Status:** data pipeline and SQL analysis queries are complete and tested. Key findings, the Power BI dashboard and the price model are in progress.

---

## Questions

1. How have average prices and the renewable share changed year by year?
2. Does midday solar push prices down, and when are the expensive evening peaks?
3. How much cheaper is an hour when renewables cover most of supply (merit-order effect)?
4. When do negative prices happen, and are they becoming more frequent?
5. What did the most expensive days have in common?
6. How big is the daily price spread, and what is it worth to shift demand or store power?

## Data

| | |
|---|---|
| Source | [SMARD.de](https://www.smard.de), Bundesnetzagentur |
| Licence | CC BY 4.0, "Bundesnetzagentur \| SMARD.de" |
| Resolution | hourly, German local time (Europe/Berlin) |
| Series | day-ahead price (DE-LU bidding zone), grid load, residual load, and generation from solar, wind onshore, wind offshore, biomass, hydro, other renewables, lignite, hard coal, natural gas, nuclear, pumped storage, other conventional |
| Units | generation and load in MWh per hour (= average MW), price in EUR/MWh |

**Definitions**

- *Renewable share* = (solar + wind onshore + wind offshore + biomass + hydro + other renewables) / total generation, calculated energy-weighted (`SUM / SUM`), not as an average of hourly shares.
- *Load-weighted price* = average price weighted by consumption in each hour, i.e. closer to what consumers actually pay than the simple average.
- 2022 is strongly affected by the gas-price crisis; the hourly-profile, merit-order and expensive-day analyses therefore use 2023 onwards.

## Project structure

```
German-Electricity-Market-Analysis/
├── src/
│   ├── 01_download_smard.py   ← downloads 15 hourly series from SMARD (cached, with retries)
│   └── 02_load_sqlite.py      ← adds date parts and shares, loads SQLite, writes a Power BI CSV
├── sql/
│   └── analysis.sql           ← 7 analysis queries, one per business question
├── tests/
│   ├── test_pipeline.py       ← offline end-to-end test of download, load and all queries
│   └── sample_week.json       ← one real week of SMARD data used by the test
├── data/                      ← created when you run the scripts
├── requirements.txt
└── README.md
```

## How to run

```bash
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

python tests/test_pipeline.py                    # offline check, takes a few seconds
python src/01_download_smard.py --start 2019-01-01   # about 10-20 minutes the first time
python src/02_load_sqlite.py
```

Then run the queries in `sql/analysis.sql` against `data/energy.db` (for example with DB Browser for SQLite), or load `data/processed/hourly_powerbi.csv` into Power BI.

## Key findings

*Coming soon.*

## Author

Sachini Hewahattage · [LinkedIn](https://www.linkedin.com/in/sachini-hewahattage)
