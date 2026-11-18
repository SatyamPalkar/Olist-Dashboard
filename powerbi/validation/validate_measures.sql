-- =============================================================================
-- Power BI measure validation — run against analytics after load
-- Compare each result to the matching DAX card (same filters: all non-canceled
-- unless noted). Tolerance: relative abs error < 0.5% or exact match for counts.
-- =============================================================================

-- 1) Total Revenue (= merchandise_sales per SQL Architect)
SELECT SUM(merchandise_sales) AS total_revenue
FROM analytics.fact_orders
WHERE is_canceled = FALSE;

-- 2) Merchandise Revenue (alias of Total Revenue)
SELECT SUM(merchandise_sales) AS merchandise_revenue
FROM analytics.fact_orders
WHERE is_canceled = FALSE;

-- 3) Freight Revenue
SELECT SUM(freight_charges) AS freight_revenue
FROM analytics.fact_orders
WHERE is_canceled = FALSE;

-- 3b) Total Order Value (GMV = merchandise + freight)
SELECT SUM(order_value) AS total_order_value
FROM analytics.fact_orders
WHERE is_canceled = FALSE;

-- 4) Total Orders
SELECT COUNT(DISTINCT order_id) AS total_orders
FROM analytics.fact_orders
WHERE is_canceled = FALSE;

-- 5) Average Order Value (AVG at order grain)
SELECT AVG(order_value) AS average_order_value
FROM analytics.fact_orders
WHERE is_canceled = FALSE;

-- 6) Unique Customers
SELECT COUNT(DISTINCT customer_key) AS unique_customers
FROM analytics.fact_orders
WHERE is_canceled = FALSE;

-- 7) Repeat Customer Rate
-- DAX: distinct customers on orders who are repeat / unique customers in filter
WITH base AS (
    SELECT DISTINCT o.customer_key
    FROM analytics.fact_orders o
    WHERE o.is_canceled = FALSE
)
SELECT
    COUNT(*) FILTER (
        WHERE c.is_repeat_customer
    )::NUMERIC / NULLIF(COUNT(*), 0) AS repeat_customer_rate
FROM base b
JOIN analytics.dim_customers c ON c.customer_key = b.customer_key;

-- 8) Revenue MoM Growth (example: latest complete month vs prior)
-- Adjust the year_month literals after profiling date range.
WITH monthly AS (
    SELECT
        d.year_month,
        SUM(o.merchandise_sales) AS revenue
    FROM analytics.fact_orders o
    JOIN analytics.dim_date d ON d.date_key = o.purchase_date_key
    WHERE o.is_canceled = FALSE
    GROUP BY d.year_month
),
ordered AS (
    SELECT
        year_month,
        revenue,
        LAG(revenue) OVER (ORDER BY year_month) AS prev_revenue
    FROM monthly
)
SELECT
    year_month,
    revenue,
    prev_revenue,
    (revenue - prev_revenue) / NULLIF(prev_revenue, 0) AS revenue_mom_growth
FROM ordered
ORDER BY year_month DESC
LIMIT 6;

-- 9) Revenue YoY Growth (month matched to prior year; merchandise)
WITH monthly AS (
    SELECT
        d.year,
        d.month,
        d.year_month,
        SUM(o.merchandise_sales) AS revenue
    FROM analytics.fact_orders o
    JOIN analytics.dim_date d ON d.date_key = o.purchase_date_key
    WHERE o.is_canceled = FALSE
    GROUP BY d.year, d.month, d.year_month
)
SELECT
    cur.year_month,
    cur.revenue AS revenue,
    pri.revenue AS revenue_prev_year,
    (cur.revenue - pri.revenue) / NULLIF(pri.revenue, 0) AS revenue_yoy_growth
FROM monthly cur
LEFT JOIN monthly pri
    ON pri.month = cur.month
   AND pri.year = cur.year - 1
ORDER BY cur.year_month DESC
LIMIT 12;

-- 10) Average Delivery Time
SELECT AVG(delivery_days) AS average_delivery_time
FROM analytics.fact_orders
WHERE is_delivered = TRUE
  AND delivery_days IS NOT NULL;

-- 11) Late Delivery Rate
SELECT
    COUNT(*) FILTER (WHERE is_late_delivery = TRUE)::NUMERIC
        / NULLIF(COUNT(*) FILTER (WHERE is_late_delivery IS NOT NULL), 0)
        AS late_delivery_rate
FROM analytics.fact_orders
WHERE is_delivered = TRUE;

-- 12) On-time Delivery Rate (complement among SLA-known delivered)
SELECT
    COUNT(*) FILTER (WHERE is_late_delivery = FALSE)::NUMERIC
        / NULLIF(COUNT(*) FILTER (WHERE is_late_delivery IS NOT NULL), 0)
        AS on_time_delivery_rate
FROM analytics.fact_orders
WHERE is_delivered = TRUE;

-- 13) Average Review Score (review fact grain — preferred)
SELECT AVG(review_score::NUMERIC) AS average_review_score
FROM analytics.fact_order_reviews;

-- Cross-check: order-level denormalised score
SELECT AVG(review_score::NUMERIC) AS average_review_score_order
FROM analytics.fact_orders
WHERE review_score IS NOT NULL;

-- 14) Item-grain revenue sanity (Product page)
SELECT
    SUM(price) AS merchandise_revenue_items,
    SUM(freight_value) AS freight_revenue_items,
    SUM(item_total) AS total_revenue_items
FROM analytics.fact_order_items;

-- 15) Payment value sanity
SELECT
    payment_type,
    SUM(payment_value) AS payment_value
FROM analytics.fact_payments
GROUP BY payment_type
ORDER BY payment_value DESC;
