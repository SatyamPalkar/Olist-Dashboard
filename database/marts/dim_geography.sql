-- analytics.dim_geography
-- Technique: UNION of customer + seller zips, LEFT JOIN geo + state seed
BEGIN;

TRUNCATE analytics.dim_geography RESTART IDENTITY CASCADE;

INSERT INTO analytics.dim_geography (
    zip_code_prefix,
    city,
    state,
    state_name,
    region,
    latitude,
    longitude
)
WITH all_zips AS (
    SELECT customer_zip_code_prefix AS zip_code_prefix, customer_city AS city, customer_state AS state
    FROM staging.stg_customers
    UNION
    SELECT seller_zip_code_prefix, seller_city, seller_state
    FROM staging.stg_sellers
),
dedup AS (
    SELECT DISTINCT ON (zip_code_prefix)
        zip_code_prefix,
        city,
        state
    FROM all_zips
    WHERE NULLIF(zip_code_prefix, '') IS NOT NULL
    ORDER BY zip_code_prefix, city, state
)
SELECT
    d.zip_code_prefix,
    COALESCE(g.city, d.city)                    AS city,
    COALESCE(g.state, d.state)                  AS state,
    s.state_name,
    s.region,
    g.avg_lat                                   AS latitude,
    g.avg_lng                                   AS longitude
FROM dedup d
LEFT JOIN staging.stg_geolocation g
    ON g.zip_code_prefix = d.zip_code_prefix
LEFT JOIN analytics.seed_brazilian_states s
    ON s.state_code = COALESCE(g.state, d.state);

COMMIT;
