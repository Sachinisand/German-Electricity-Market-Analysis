-- =====================================================================
-- German electricity market analysis (SMARD data, table `hourly`)
-- Run in DB Browser for SQLite, DBeaver, or:  sqlite3 data/energy.db < sql/analysis.sql
-- Shares are energy-weighted (SUM / SUM), not averages of hourly shares.
-- =====================================================================


-- Q1. Yearly overview: how have prices and the renewable share changed?
SELECT
    year,
    ROUND(AVG(price_eur_mwh), 1)                               AS avg_price_eur_mwh,
    ROUND(SUM(price_eur_mwh * load_mwh) / SUM(load_mwh), 1)    AS load_weighted_price,
    ROUND(MAX(price_eur_mwh), 0)                               AS max_price,
    ROUND(100.0 * SUM(renewable_mwh) / SUM(generation_mwh), 1) AS renewable_share_pct,
    SUM(is_negative_price)                                     AS negative_price_hours,
    ROUND(SUM(load_mwh) / 1e6, 1)                              AS load_twh
FROM hourly
GROUP BY year
ORDER BY year;


-- Q2. Monthly trend: price and renewable share side by side.
SELECT
    year, month,
    ROUND(AVG(price_eur_mwh), 1)                               AS avg_price_eur_mwh,
    ROUND(100.0 * SUM(renewable_mwh) / SUM(generation_mwh), 1) AS renewable_share_pct,
    ROUND(100.0 * SUM(solar_mwh) / SUM(generation_mwh), 1)     AS solar_share_pct,
    ROUND(100.0 * SUM(wind_onshore_mwh + wind_offshore_mwh) / SUM(generation_mwh), 1) AS wind_share_pct
FROM hourly
GROUP BY year, month
ORDER BY year, month;


-- Q3. Daily price profile by season ("duck curve"):
--     does midday solar push prices down, and when are the evening peaks?
SELECT
    season, hour,
    ROUND(AVG(price_eur_mwh), 1)  AS avg_price_eur_mwh,
    ROUND(AVG(solar_mwh) / 1000, 1) AS avg_solar_gw
FROM hourly
WHERE year >= 2023                -- recent market, after the 2022 energy crisis
GROUP BY season, hour
ORDER BY season, hour;


-- Q4. Merit-order effect: how much cheaper is power when renewables cover more of supply?
SELECT
    CAST(renewable_share * 10 AS INT) * 10        AS renewable_share_from_pct,
    COUNT(*)                                      AS hours,
    ROUND(AVG(price_eur_mwh), 1)                  AS avg_price_eur_mwh,
    ROUND(100.0 * AVG(is_negative_price), 1)      AS pct_hours_negative
FROM hourly
WHERE year >= 2023 AND renewable_share IS NOT NULL
GROUP BY renewable_share_from_pct
ORDER BY renewable_share_from_pct;


-- Q5. Negative prices: when do they happen?
SELECT
    year, hour,
    SUM(is_negative_price)                                      AS negative_hours,
    ROUND(AVG(CASE WHEN is_negative_price = 1 THEN price_eur_mwh END), 1) AS avg_negative_price
FROM hourly
GROUP BY year, hour
HAVING negative_hours > 0
ORDER BY year, hour;


-- Q6. The 10 most expensive days, and what the system looked like on them.
SELECT
    date,
    ROUND(AVG(price_eur_mwh), 1)                               AS avg_price_eur_mwh,
    ROUND(AVG(residual_load_mwh) / 1000, 1)                    AS avg_residual_load_gw,
    ROUND(AVG(wind_onshore_mwh + wind_offshore_mwh) / 1000, 1) AS avg_wind_gw,
    ROUND(100.0 * SUM(renewable_mwh) / SUM(generation_mwh), 1) AS renewable_share_pct
FROM hourly
WHERE year >= 2023
GROUP BY date
ORDER BY avg_price_eur_mwh DESC
LIMIT 10;


-- Q7. Price spread per day (max - min): the value of shifting demand or storing power.
SELECT
    year,
    ROUND(AVG(daily_spread), 1) AS avg_daily_spread_eur_mwh,
    ROUND(MAX(daily_spread), 0) AS max_daily_spread_eur_mwh
FROM (
    SELECT year, date, MAX(price_eur_mwh) - MIN(price_eur_mwh) AS daily_spread
    FROM hourly
    GROUP BY year, date
)
GROUP BY year
ORDER BY year;
