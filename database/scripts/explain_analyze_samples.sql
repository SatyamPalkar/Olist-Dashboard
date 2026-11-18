-- =============================================================================
-- EXPLAIN ANALYZE samples for expensive reporting paths.
-- Run after data load. Review Seq Scan vs Index Scan; adjust indexes if needed.
-- =============================================================================

\echo '=== EXPLAIN: sales by month ==='
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT
    d.year_month,
    SUM(fo.merchandise_sales) AS merchandise_sales
FROM analytics.fact_orders fo
JOIN analytics.dim_date d ON d.date_key = fo.purchase_date_key
WHERE fo.is_canceled = FALSE
GROUP BY d.year_month
ORDER BY d.year_month;

\echo '=== EXPLAIN: revenue by category ==='
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT
    dp.product_category_name_english,
    SUM(foi.price) AS merchandise_sales
FROM analytics.fact_order_items foi
JOIN analytics.dim_products dp ON dp.product_key = foi.product_key
JOIN analytics.fact_orders fo ON fo.order_key = foi.order_key
WHERE fo.is_canceled = FALSE
GROUP BY dp.product_category_name_english
ORDER BY merchandise_sales DESC;

\echo '=== EXPLAIN: top products (window) ==='
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT product_id, merchandise_sales, revenue_rank
FROM analytics.vw_top_10_products;

\echo '=== EXPLAIN: seller performance ==='
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT seller_id, merchandise_sales, sales_rank
FROM analytics.vw_seller_performance
LIMIT 50;

\echo '=== EXPLAIN: materialised monthly (should be cheap) ==='
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT year_month, merchandise_sales, order_count
FROM analytics.mv_monthly_sales
ORDER BY year_month;
