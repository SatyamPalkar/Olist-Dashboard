-- analytics.dim_sellers
BEGIN;

TRUNCATE analytics.dim_sellers RESTART IDENTITY CASCADE;

INSERT INTO analytics.dim_sellers (
    seller_id,
    geography_key,
    zip_code_prefix,
    city,
    state
)
SELECT
    s.seller_id,
    g.geography_key,
    s.seller_zip_code_prefix,
    s.seller_city,
    s.seller_state
FROM staging.stg_sellers s
LEFT JOIN analytics.dim_geography g
    ON g.zip_code_prefix = s.seller_zip_code_prefix;

INSERT INTO analytics.dim_sellers (seller_id, zip_code_prefix, city, state)
VALUES ('__UNKNOWN__', NULL, 'unknown', 'XX')
ON CONFLICT (seller_id) DO NOTHING;

COMMIT;
