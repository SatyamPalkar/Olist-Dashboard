-- =============================================================================
-- Materialised view: monthly sales summary
-- Justification: frequently queried by Power BI; stable historical data;
--                expensive GROUP BY across fact_orders + dim_date.
-- Refresh after mart rebuild: REFRESH MATERIALIZED VIEW analytics.mv_monthly_sales;
-- =============================================================================

DROP MATERIALIZED VIEW IF EXISTS analytics.mv_monthly_sales;

CREATE MATERIALIZED VIEW analytics.mv_monthly_sales AS
SELECT
    d.year,
    d.month,
    d.year_month,
    d.month_name,
    COUNT(DISTINCT fo.order_id)                         AS order_count,
    SUM(fo.merchandise_sales)                           AS merchandise_sales,
    SUM(fo.freight_charges)                             AS freight_charges,
    SUM(fo.order_value)                                 AS order_value,
    SUM(fo.payment_amount)                              AS payment_amount,
    ROUND(AVG(fo.order_value), 2)                       AS avg_order_value,
    COUNT(*) FILTER (WHERE fo.is_late_delivery)         AS late_order_count
FROM analytics.fact_orders fo
JOIN analytics.dim_date d
    ON d.date_key = fo.purchase_date_key
WHERE fo.is_canceled = FALSE
GROUP BY d.year, d.month, d.year_month, d.month_name
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_monthly_sales_ym
    ON analytics.mv_monthly_sales (year_month);

COMMENT ON MATERIALIZED VIEW analytics.mv_monthly_sales IS
    'Cached monthly sales for Power BI. Refresh after fact_orders rebuild.';

-- Category monthly (second useful MV)
DROP MATERIALIZED VIEW IF EXISTS analytics.mv_category_monthly_sales;

CREATE MATERIALIZED VIEW analytics.mv_category_monthly_sales AS
SELECT
    d.year_month,
    COALESCE(dp.product_category_name_english, 'unknown') AS product_category,
    SUM(foi.price)                                        AS merchandise_sales,
    SUM(foi.freight_value)                                AS freight_charges,
    COUNT(*)                                              AS line_count,
    COUNT(DISTINCT foi.order_id)                          AS order_count
FROM analytics.fact_order_items foi
JOIN analytics.fact_orders fo
    ON fo.order_key = foi.order_key
JOIN analytics.dim_date d
    ON d.date_key = foi.purchase_date_key
JOIN analytics.dim_products dp
    ON dp.product_key = foi.product_key
WHERE fo.is_canceled = FALSE
GROUP BY d.year_month, COALESCE(dp.product_category_name_english, 'unknown')
WITH DATA;

CREATE INDEX IF NOT EXISTS ix_mv_category_monthly_ym
    ON analytics.mv_category_monthly_sales (year_month);

CREATE INDEX IF NOT EXISTS ix_mv_category_monthly_cat
    ON analytics.mv_category_monthly_sales (product_category);

COMMENT ON MATERIALIZED VIEW analytics.mv_category_monthly_sales IS
    'Cached category × month merchandise sales. Refresh after fact_order_items rebuild.';
