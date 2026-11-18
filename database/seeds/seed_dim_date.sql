-- =============================================================================
-- Seed / generate dim_date for 2016-01-01 → 2018-12-31 (Olist window + buffer)
-- Extends slightly before/after for edge timestamps.
-- Safe to re-run.
-- =============================================================================
BEGIN;

TRUNCATE analytics.dim_date CASCADE;

INSERT INTO analytics.dim_date (
    date_key,
    full_date,
    year,
    quarter,
    month,
    month_name,
    month_name_short,
    day_of_month,
    day_of_week,
    day_name,
    week_of_year,
    year_month,
    is_weekend
)
SELECT
    TO_CHAR(d, 'YYYYMMDD')::INTEGER                         AS date_key,
    d::DATE                                                 AS full_date,
    EXTRACT(YEAR FROM d)::SMALLINT                          AS year,
    EXTRACT(QUARTER FROM d)::SMALLINT                       AS quarter,
    EXTRACT(MONTH FROM d)::SMALLINT                         AS month,
    TRIM(TO_CHAR(d, 'Month'))                               AS month_name,
    TO_CHAR(d, 'Mon')                                       AS month_name_short,
    EXTRACT(DAY FROM d)::SMALLINT                           AS day_of_month,
    EXTRACT(ISODOW FROM d)::SMALLINT                        AS day_of_week,
    TRIM(TO_CHAR(d, 'Day'))                                 AS day_name,
    EXTRACT(WEEK FROM d)::SMALLINT                          AS week_of_year,
    TO_CHAR(d, 'YYYY-MM')                                   AS year_month,
    EXTRACT(ISODOW FROM d) IN (6, 7)                        AS is_weekend
FROM generate_series(
    DATE '2016-01-01',
    DATE '2018-12-31',
    INTERVAL '1 day'
) AS g(d);

COMMIT;
