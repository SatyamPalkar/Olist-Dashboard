-- analytics.fact_orders
-- Grain: one order
-- Technique: CTEs pre-aggregate items + payments BEFORE joining (anti double-count)
BEGIN;

TRUNCATE analytics.fact_orders RESTART IDENTITY CASCADE;

INSERT INTO analytics.fact_orders (
    order_id,
    customer_key,
    customer_geography_key,
    purchase_date_key,
    approved_date_key,
    delivered_customer_date_key,
    estimated_delivery_date_key,
    order_status,
    is_delivered,
    is_canceled,
    merchandise_sales,
    freight_charges,
    order_value,
    payment_amount,
    item_count,
    payment_count,
    delivery_days,
    is_late_delivery,
    review_score
)
WITH item_agg AS (
    SELECT
        order_id,
        SUM(price)::NUMERIC(14, 2)              AS merchandise_sales,
        SUM(freight_value)::NUMERIC(14, 2)      AS freight_charges,
        SUM(item_total)::NUMERIC(14, 2)         AS order_value,
        COUNT(*)::INTEGER                       AS item_count
    FROM staging.stg_order_items
    GROUP BY order_id
),
payment_agg AS (
    SELECT
        order_id,
        SUM(payment_value)::NUMERIC(14, 2)      AS payment_amount,
        COUNT(*)::INTEGER                       AS payment_count
    FROM staging.stg_order_payments
    GROUP BY order_id
),
review_pick AS (
    -- One score per order for order-grain reporting (latest review_creation_date)
    SELECT
        order_id,
        review_score,
        ROW_NUMBER() OVER (
            PARTITION BY order_id
            ORDER BY review_creation_date DESC NULLS LAST, review_sk DESC
        ) AS rn
    FROM staging.stg_order_reviews
)
SELECT
    o.order_id,
    dc.customer_key,
    dc.geography_key                                                    AS customer_geography_key,
    TO_CHAR(o.purchase_date, 'YYYYMMDD')::INTEGER                       AS purchase_date_key,
    CASE WHEN o.order_approved_at IS NOT NULL
         THEN TO_CHAR(o.order_approved_at::DATE, 'YYYYMMDD')::INTEGER
    END                                                                 AS approved_date_key,
    CASE WHEN o.order_delivered_customer_date IS NOT NULL
         THEN TO_CHAR(o.order_delivered_customer_date::DATE, 'YYYYMMDD')::INTEGER
    END                                                                 AS delivered_customer_date_key,
    CASE WHEN o.order_estimated_delivery_date IS NOT NULL
         THEN TO_CHAR(o.order_estimated_delivery_date::DATE, 'YYYYMMDD')::INTEGER
    END                                                                 AS estimated_delivery_date_key,
    o.order_status,
    o.is_delivered,
    o.is_canceled,
    COALESCE(ia.merchandise_sales, 0)                                   AS merchandise_sales,
    COALESCE(ia.freight_charges, 0)                                     AS freight_charges,
    COALESCE(ia.order_value, 0)                                         AS order_value,
    COALESCE(pa.payment_amount, 0)                                      AS payment_amount,
    COALESCE(ia.item_count, 0)                                          AS item_count,
    COALESCE(pa.payment_count, 0)                                       AS payment_count,
    o.delivery_days,
    o.is_late_delivery,
    rp.review_score
FROM staging.stg_orders o
JOIN staging.stg_customers sc
    ON sc.customer_id = o.customer_id
JOIN analytics.dim_customers dc
    ON dc.customer_unique_id = sc.customer_unique_id
LEFT JOIN item_agg ia
    ON ia.order_id = o.order_id
LEFT JOIN payment_agg pa
    ON pa.order_id = o.order_id
LEFT JOIN review_pick rp
    ON rp.order_id = o.order_id AND rp.rn = 1
-- Ensure date keys exist (orphan dates outside seed range are excluded via INNER on purchase)
JOIN analytics.dim_date dd
    ON dd.date_key = TO_CHAR(o.purchase_date, 'YYYYMMDD')::INTEGER;

COMMIT;
