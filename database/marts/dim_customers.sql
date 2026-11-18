-- analytics.dim_customers
-- Grain: customer_unique_id
-- Technique: CTE, window functions (ROW_NUMBER), aggregations for first/last order
-- SCD: Type 1 (overwrite) — source is a static historical dump
BEGIN;

TRUNCATE analytics.dim_customers RESTART IDENTITY CASCADE;

INSERT INTO analytics.dim_customers (
    customer_unique_id,
    geography_key,
    zip_code_prefix,
    city,
    state,
    first_order_date,
    last_order_date,
    order_count,
    is_repeat_customer
)
WITH customer_orders AS (
    SELECT
        c.customer_unique_id,
        c.customer_id,
        c.customer_zip_code_prefix,
        c.customer_city,
        c.customer_state,
        o.purchase_date,
        o.order_id
    FROM staging.stg_customers c
    LEFT JOIN staging.stg_orders o
        ON o.customer_id = c.customer_id
),
order_stats AS (
    SELECT
        customer_unique_id,
        MIN(purchase_date)                          AS first_order_date,
        MAX(purchase_date)                          AS last_order_date,
        COUNT(DISTINCT order_id)::INTEGER           AS order_count
    FROM customer_orders
    GROUP BY customer_unique_id
),
latest_attr AS (
    -- Attributes from the customer_id row tied to the most recent order
    SELECT
        customer_unique_id,
        customer_zip_code_prefix,
        customer_city,
        customer_state,
        ROW_NUMBER() OVER (
            PARTITION BY customer_unique_id
            ORDER BY purchase_date DESC NULLS LAST, customer_id
        ) AS rn
    FROM customer_orders
)
SELECT
    la.customer_unique_id,
    g.geography_key,
    la.customer_zip_code_prefix                     AS zip_code_prefix,
    la.customer_city                                AS city,
    la.customer_state                               AS state,
    os.first_order_date,
    os.last_order_date,
    COALESCE(os.order_count, 0)                     AS order_count,
    COALESCE(os.order_count, 0) > 1                 AS is_repeat_customer
FROM latest_attr la
JOIN order_stats os
    ON os.customer_unique_id = la.customer_unique_id
LEFT JOIN analytics.dim_geography g
    ON g.zip_code_prefix = la.customer_zip_code_prefix
WHERE la.rn = 1;

COMMIT;
