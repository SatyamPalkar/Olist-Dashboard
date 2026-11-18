-- =============================================================================
-- Standalone KPI query pack (same logic as views — for ad-hoc / documentation).
-- Run after analytics marts are loaded.
-- Avoids SELECT *.
-- =============================================================================

-- 1. Total sales by month
SELECT year, month, year_month, order_count, merchandise_sales, freight_charges, order_value
FROM analytics.vw_sales_by_month;

-- 2. Revenue by product category
SELECT product_category, order_count, merchandise_sales, freight_charges
FROM analytics.vw_revenue_by_category
LIMIT 50;

-- 3. Top 10 products by revenue
SELECT revenue_rank, product_id, product_category, merchandise_sales, units_sold
FROM analytics.vw_top_10_products;

-- 4. Sales by geography
SELECT region, state, state_name, order_count, merchandise_sales
FROM analytics.vw_sales_by_geography;

-- 5. Average order value
SELECT order_count, avg_merchandise_sales, avg_order_value, avg_payment_amount
FROM analytics.vw_average_order_value;

-- 6. Month-over-month growth
SELECT year_month, merchandise_sales, prior_month_sales, mom_growth_pct, running_total_sales
FROM analytics.vw_mom_growth;

-- 7. Payment distribution
SELECT payment_type, payment_count, payment_amount, pct_of_payment_amount, avg_installments
FROM analytics.vw_payment_distribution;

-- 8. Average delivery time
SELECT delivered_orders, avg_delivery_days, median_delivery_days
FROM analytics.vw_avg_delivery_time;

-- 9. Late delivery percentage
SELECT delivered_with_estimate, late_deliveries, late_delivery_pct
FROM analytics.vw_late_delivery_pct;

-- 10. Customer repeat purchase behaviour
SELECT customer_segment, customer_count, pct_of_customers, avg_orders, avg_lifetime_merchandise_sales
FROM analytics.vw_customer_repeat_behaviour;

-- 11. Seller performance (top 25)
SELECT seller_id, seller_state, order_count, merchandise_sales, avg_review_score, sales_rank
FROM analytics.vw_seller_performance
LIMIT 25;

-- 12. Review score distribution
SELECT review_score, review_count, pct_of_reviews, reviews_with_comment
FROM analytics.vw_review_score_distribution;
