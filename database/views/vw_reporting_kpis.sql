-- =============================================================================
-- Reusable reporting views + 12 analytical KPI queries
-- Techniques: JOIN, CTE, CASE, window functions, aggregations, ranking,
--             running totals, date functions, subqueries
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Helper: delivered orders only (common filter for delivery KPIs)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW analytics.vw_fact_orders_delivered AS
SELECT
    fo.order_key,
    fo.order_id,
    fo.customer_key,
    fo.customer_geography_key,
    fo.purchase_date_key,
    fo.order_status,
    fo.merchandise_sales,
    fo.freight_charges,
    fo.order_value,
    fo.payment_amount,
    fo.item_count,
    fo.delivery_days,
    fo.is_late_delivery,
    fo.review_score
FROM analytics.fact_orders fo
WHERE fo.is_delivered = TRUE;

COMMENT ON VIEW analytics.vw_fact_orders_delivered IS
    'Delivered orders only — use for delivery-time and late-delivery KPIs.';

-- ---------------------------------------------------------------------------
-- 1. Total sales by month
-- Revenue = merchandise_sales (SUM price). Freight reported separately.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW analytics.vw_sales_by_month AS
SELECT
    d.year,
    d.month,
    d.year_month,
    d.month_name,
    COUNT(DISTINCT fo.order_id)                         AS order_count,
    SUM(fo.merchandise_sales)                           AS merchandise_sales,
    SUM(fo.freight_charges)                             AS freight_charges,
    SUM(fo.order_value)                                 AS order_value,
    SUM(fo.payment_amount)                              AS payment_amount
FROM analytics.fact_orders fo
JOIN analytics.dim_date d
    ON d.date_key = fo.purchase_date_key
WHERE fo.is_canceled = FALSE
GROUP BY d.year, d.month, d.year_month, d.month_name
ORDER BY d.year, d.month;

COMMENT ON VIEW analytics.vw_sales_by_month IS
    'KPI 1 — Total sales by month. merchandise_sales is canonical revenue.';

-- ---------------------------------------------------------------------------
-- 2. Revenue by product category
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW analytics.vw_revenue_by_category AS
SELECT
    COALESCE(dp.product_category_name_english, 'unknown') AS product_category,
    COUNT(*)                                              AS line_count,
    COUNT(DISTINCT foi.order_id)                          AS order_count,
    SUM(foi.price)                                        AS merchandise_sales,
    SUM(foi.freight_value)                                AS freight_charges,
    SUM(foi.item_total)                                   AS order_value
FROM analytics.fact_order_items foi
JOIN analytics.dim_products dp
    ON dp.product_key = foi.product_key
JOIN analytics.fact_orders fo
    ON fo.order_key = foi.order_key
WHERE fo.is_canceled = FALSE
GROUP BY COALESCE(dp.product_category_name_english, 'unknown')
ORDER BY merchandise_sales DESC;

COMMENT ON VIEW analytics.vw_revenue_by_category IS
    'KPI 2 — Revenue by product category (from order items; no payment join).';

-- ---------------------------------------------------------------------------
-- 3. Top 10 products by revenue
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW analytics.vw_top_10_products AS
WITH product_revenue AS (
    SELECT
        dp.product_id,
        COALESCE(dp.product_category_name_english, 'unknown') AS product_category,
        SUM(foi.price)                                        AS merchandise_sales,
        SUM(foi.freight_value)                                AS freight_charges,
        COUNT(*)                                              AS units_sold,
        COUNT(DISTINCT foi.order_id)                          AS order_count
    FROM analytics.fact_order_items foi
    JOIN analytics.dim_products dp
        ON dp.product_key = foi.product_key
    JOIN analytics.fact_orders fo
        ON fo.order_key = foi.order_key
    WHERE fo.is_canceled = FALSE
      AND dp.product_id <> '__UNKNOWN__'
    GROUP BY dp.product_id, COALESCE(dp.product_category_name_english, 'unknown')
),
ranked AS (
    SELECT
        product_id,
        product_category,
        merchandise_sales,
        freight_charges,
        units_sold,
        order_count,
        RANK() OVER (ORDER BY merchandise_sales DESC) AS revenue_rank
    FROM product_revenue
)
SELECT
    revenue_rank,
    product_id,
    product_category,
    merchandise_sales,
    freight_charges,
    units_sold,
    order_count
FROM ranked
WHERE revenue_rank <= 10
ORDER BY revenue_rank, product_id;

COMMENT ON VIEW analytics.vw_top_10_products IS
    'KPI 3 — Top 10 products by merchandise_sales (RANK).';

-- ---------------------------------------------------------------------------
-- 4. Sales by geography (customer state / region)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW analytics.vw_sales_by_geography AS
SELECT
    COALESCE(g.region, 'Unknown')           AS region,
    COALESCE(g.state, 'XX')                 AS state,
    COALESCE(g.state_name, 'Unknown')      AS state_name,
    COUNT(DISTINCT fo.order_id)             AS order_count,
    SUM(fo.merchandise_sales)               AS merchandise_sales,
    SUM(fo.freight_charges)                 AS freight_charges,
    SUM(fo.order_value)                     AS order_value
FROM analytics.fact_orders fo
LEFT JOIN analytics.dim_geography g
    ON g.geography_key = fo.customer_geography_key
WHERE fo.is_canceled = FALSE
GROUP BY
    COALESCE(g.region, 'Unknown'),
    COALESCE(g.state, 'XX'),
    COALESCE(g.state_name, 'Unknown')
ORDER BY merchandise_sales DESC;

COMMENT ON VIEW analytics.vw_sales_by_geography IS
    'KPI 4 — Sales by customer geography (state/region).';

-- ---------------------------------------------------------------------------
-- 5. Average order value
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW analytics.vw_average_order_value AS
SELECT
    COUNT(DISTINCT order_id)                                    AS order_count,
    SUM(merchandise_sales)                                      AS total_merchandise_sales,
    SUM(order_value)                                            AS total_order_value,
    ROUND(AVG(merchandise_sales), 2)                            AS avg_merchandise_sales,
    ROUND(AVG(order_value), 2)                                  AS avg_order_value,
    ROUND(AVG(payment_amount), 2)                               AS avg_payment_amount
FROM analytics.fact_orders
WHERE is_canceled = FALSE;

COMMENT ON VIEW analytics.vw_average_order_value IS
    'KPI 5 — AOV. avg_order_value = AVG(merchandise + freight) at order grain.';

-- ---------------------------------------------------------------------------
-- 6. Month-over-month growth (+ running total)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW analytics.vw_mom_growth AS
WITH monthly AS (
    SELECT
        d.year,
        d.month,
        d.year_month,
        SUM(fo.merchandise_sales) AS merchandise_sales,
        COUNT(DISTINCT fo.order_id) AS order_count
    FROM analytics.fact_orders fo
    JOIN analytics.dim_date d
        ON d.date_key = fo.purchase_date_key
    WHERE fo.is_canceled = FALSE
    GROUP BY d.year, d.month, d.year_month
)
SELECT
    year,
    month,
    year_month,
    merchandise_sales,
    order_count,
    LAG(merchandise_sales) OVER (ORDER BY year, month)              AS prior_month_sales,
    ROUND(
        100.0 * (
            merchandise_sales
            - LAG(merchandise_sales) OVER (ORDER BY year, month)
        )
        / NULLIF(LAG(merchandise_sales) OVER (ORDER BY year, month), 0),
        2
    )                                                               AS mom_growth_pct,
    SUM(merchandise_sales) OVER (
        ORDER BY year, month
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                                                               AS running_total_sales
FROM monthly
ORDER BY year, month;

COMMENT ON VIEW analytics.vw_mom_growth IS
    'KPI 6 — MoM growth % on merchandise_sales + running total (window functions).';

-- ---------------------------------------------------------------------------
-- 7. Payment distribution
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW analytics.vw_payment_distribution AS
SELECT
    payment_type,
    COUNT(*)                                                        AS payment_count,
    COUNT(DISTINCT order_id)                                        AS order_count,
    SUM(payment_value)                                              AS payment_amount,
    ROUND(
        100.0 * SUM(payment_value)
        / NULLIF(SUM(SUM(payment_value)) OVER (), 0),
        2
    )                                                               AS pct_of_payment_amount,
    ROUND(AVG(payment_installments), 2)                             AS avg_installments
FROM analytics.fact_payments
GROUP BY payment_type
ORDER BY payment_amount DESC;

COMMENT ON VIEW analytics.vw_payment_distribution IS
    'KPI 7 — Payment type distribution (payment fact only — no item join).';

-- ---------------------------------------------------------------------------
-- 8. Average delivery time
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW analytics.vw_avg_delivery_time AS
SELECT
    COUNT(*)                                                        AS delivered_orders,
    ROUND(AVG(delivery_days), 2)                                    AS avg_delivery_days,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY delivery_days)::NUMERIC, 2)
                                                                    AS median_delivery_days,
    ROUND(MIN(delivery_days), 2)                                    AS min_delivery_days,
    ROUND(MAX(delivery_days), 2)                                    AS max_delivery_days
FROM analytics.fact_orders
WHERE is_delivered = TRUE
  AND delivery_days IS NOT NULL;

COMMENT ON VIEW analytics.vw_avg_delivery_time IS
    'KPI 8 — Average / median delivery days (purchase → customer delivery).';

-- ---------------------------------------------------------------------------
-- 9. Late delivery percentage
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW analytics.vw_late_delivery_pct AS
SELECT
    COUNT(*)                                                        AS delivered_with_estimate,
    COUNT(*) FILTER (WHERE is_late_delivery = TRUE)                 AS late_deliveries,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE is_late_delivery = TRUE)
        / NULLIF(COUNT(*), 0),
        2
    )                                                               AS late_delivery_pct
FROM analytics.fact_orders
WHERE is_delivered = TRUE
  AND is_late_delivery IS NOT NULL;

COMMENT ON VIEW analytics.vw_late_delivery_pct IS
    'KPI 9 — Late delivery %: delivered_customer_date > estimated_delivery_date.';

-- ---------------------------------------------------------------------------
-- 10. Customer repeat purchase behaviour
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW analytics.vw_customer_repeat_behaviour AS
WITH customer_orders AS (
    SELECT
        dc.customer_key,
        dc.customer_unique_id,
        dc.is_repeat_customer,
        COUNT(DISTINCT fo.order_id)                 AS order_count,
        SUM(fo.merchandise_sales)                   AS lifetime_merchandise_sales,
        MIN(d.full_date)                            AS first_order_date,
        MAX(d.full_date)                            AS last_order_date
    FROM analytics.fact_orders fo
    JOIN analytics.dim_customers dc
        ON dc.customer_key = fo.customer_key
    JOIN analytics.dim_date d
        ON d.date_key = fo.purchase_date_key
    WHERE fo.is_canceled = FALSE
    GROUP BY dc.customer_key, dc.customer_unique_id, dc.is_repeat_customer
)
SELECT
    CASE WHEN order_count = 1 THEN 'one_time' ELSE 'repeat' END AS customer_segment,
    COUNT(*)                                                    AS customer_count,
    ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0), 2)
                                                                AS pct_of_customers,
    ROUND(AVG(order_count), 2)                                  AS avg_orders,
    ROUND(AVG(lifetime_merchandise_sales), 2)                   AS avg_lifetime_merchandise_sales,
    SUM(lifetime_merchandise_sales)                             AS total_merchandise_sales
FROM customer_orders
GROUP BY CASE WHEN order_count = 1 THEN 'one_time' ELSE 'repeat' END
ORDER BY customer_segment;

COMMENT ON VIEW analytics.vw_customer_repeat_behaviour IS
    'KPI 10 — Repeat vs one-time customers (customer_unique_id).';

-- ---------------------------------------------------------------------------
-- 11. Seller performance
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW analytics.vw_seller_performance AS
WITH seller_metrics AS (
    SELECT
        ds.seller_key,
        ds.seller_id,
        ds.state                                                 AS seller_state,
        COUNT(*)                                                  AS lines_sold,
        COUNT(DISTINCT foi.order_id)                              AS order_count,
        SUM(foi.price)                                            AS merchandise_sales,
        SUM(foi.freight_value)                                    AS freight_charges,
        AVG(fo.review_score)::NUMERIC(4, 2)                       AS avg_review_score
    FROM analytics.fact_order_items foi
    JOIN analytics.dim_sellers ds
        ON ds.seller_key = foi.seller_key
    JOIN analytics.fact_orders fo
        ON fo.order_key = foi.order_key
    WHERE fo.is_canceled = FALSE
      AND ds.seller_id <> '__UNKNOWN__'
    GROUP BY ds.seller_key, ds.seller_id, ds.state
)
SELECT
    seller_id,
    seller_state,
    lines_sold,
    order_count,
    merchandise_sales,
    freight_charges,
    avg_review_score,
    RANK() OVER (ORDER BY merchandise_sales DESC)                 AS sales_rank,
    DENSE_RANK() OVER (ORDER BY avg_review_score DESC NULLS LAST) AS review_rank
FROM seller_metrics
ORDER BY merchandise_sales DESC;

COMMENT ON VIEW analytics.vw_seller_performance IS
    'KPI 11 — Seller performance ranked by merchandise_sales and review score.';

-- ---------------------------------------------------------------------------
-- 12. Review score distribution
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW analytics.vw_review_score_distribution AS
SELECT
    review_score,
    COUNT(*)                                                        AS review_count,
    ROUND(
        100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0),
        2
    )                                                               AS pct_of_reviews,
    COUNT(*) FILTER (WHERE has_comment)                             AS reviews_with_comment
FROM analytics.fact_order_reviews
GROUP BY review_score
ORDER BY review_score;

COMMENT ON VIEW analytics.vw_review_score_distribution IS
    'KPI 12 — Review score distribution (1–5).';
