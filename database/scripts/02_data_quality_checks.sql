-- =============================================================================
-- Post-load data quality checks (expect 0-row anomaly sets where noted).
-- =============================================================================

\echo '=== Row counts ==='
SELECT 'raw.olist_orders' AS table_name, COUNT(*) AS n FROM raw.olist_orders
UNION ALL SELECT 'staging.stg_orders', COUNT(*) FROM staging.stg_orders
UNION ALL SELECT 'analytics.fact_orders', COUNT(*) FROM analytics.fact_orders
UNION ALL SELECT 'analytics.fact_order_items', COUNT(*) FROM analytics.fact_order_items
UNION ALL SELECT 'analytics.fact_payments', COUNT(*) FROM analytics.fact_payments
UNION ALL SELECT 'analytics.fact_order_reviews', COUNT(*) FROM analytics.fact_order_reviews
UNION ALL SELECT 'analytics.dim_customers', COUNT(*) FROM analytics.dim_customers
UNION ALL SELECT 'analytics.dim_products', COUNT(*) FROM analytics.dim_products
UNION ALL SELECT 'analytics.dim_sellers', COUNT(*) FROM analytics.dim_sellers
ORDER BY 1;

\echo '=== Orphan order items (no order) — expect 0 ==='
SELECT COUNT(*) AS orphan_items
FROM staging.stg_order_items i
LEFT JOIN staging.stg_orders o ON o.order_id = i.order_id
WHERE o.order_id IS NULL;

\echo '=== Orders missing from fact (date out of range?) ==='
SELECT COUNT(*) AS missing_fact_orders
FROM staging.stg_orders o
LEFT JOIN analytics.fact_orders fo ON fo.order_id = o.order_id
WHERE fo.order_id IS NULL;

\echo '=== Payment vs item total discrepancy sample (informational) ==='
SELECT
    fo.order_id,
    fo.order_value,
    fo.payment_amount,
    (fo.payment_amount - fo.order_value) AS delta
FROM analytics.fact_orders fo
WHERE fo.order_value > 0
  AND ABS(fo.payment_amount - fo.order_value) > 1.00
ORDER BY ABS(fo.payment_amount - fo.order_value) DESC
LIMIT 20;

\echo '=== Repeat customer sanity ==='
SELECT
    COUNT(*) FILTER (WHERE is_repeat_customer) AS repeat_customers,
    COUNT(*) FILTER (WHERE NOT is_repeat_customer) AS one_time_customers
FROM analytics.dim_customers;
