-- staging.stg_orders
-- Technique: CAST timestamps, CASE, date functions, derived late-delivery flag
BEGIN;

TRUNCATE staging.stg_orders CASCADE;

INSERT INTO staging.stg_orders (
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_approved_at,
    order_delivered_carrier_date,
    order_delivered_customer_date,
    order_estimated_delivery_date,
    purchase_date,
    is_delivered,
    is_canceled,
    delivery_days,
    is_late_delivery
)
SELECT
    TRIM(o.order_id)                                                        AS order_id,
    TRIM(o.customer_id)                                                     AS customer_id,
    LOWER(TRIM(o.order_status))                                             AS order_status,
    TRIM(o.order_purchase_timestamp)::TIMESTAMP                             AS order_purchase_timestamp,
    NULLIF(TRIM(o.order_approved_at), '')::TIMESTAMP                        AS order_approved_at,
    NULLIF(TRIM(o.order_delivered_carrier_date), '')::TIMESTAMP             AS order_delivered_carrier_date,
    NULLIF(TRIM(o.order_delivered_customer_date), '')::TIMESTAMP            AS order_delivered_customer_date,
    NULLIF(TRIM(o.order_estimated_delivery_date), '')::TIMESTAMP            AS order_estimated_delivery_date,
    (TRIM(o.order_purchase_timestamp)::TIMESTAMP)::DATE                     AS purchase_date,
    LOWER(TRIM(o.order_status)) = 'delivered'                               AS is_delivered,
    LOWER(TRIM(o.order_status)) = 'canceled'                                AS is_canceled,
    CASE
        WHEN NULLIF(TRIM(o.order_delivered_customer_date), '') IS NOT NULL
         AND NULLIF(TRIM(o.order_purchase_timestamp), '') IS NOT NULL
        THEN EXTRACT(
                EPOCH FROM (
                    NULLIF(TRIM(o.order_delivered_customer_date), '')::TIMESTAMP
                    - TRIM(o.order_purchase_timestamp)::TIMESTAMP
                )
             ) / 86400.0
        ELSE NULL
    END                                                                     AS delivery_days,
    CASE
        WHEN NULLIF(TRIM(o.order_delivered_customer_date), '') IS NOT NULL
         AND NULLIF(TRIM(o.order_estimated_delivery_date), '') IS NOT NULL
        THEN NULLIF(TRIM(o.order_delivered_customer_date), '')::TIMESTAMP
             > NULLIF(TRIM(o.order_estimated_delivery_date), '')::TIMESTAMP
        ELSE NULL
    END                                                                     AS is_late_delivery
FROM raw.olist_orders o
WHERE NULLIF(TRIM(o.order_id), '') IS NOT NULL
  AND NULLIF(TRIM(o.customer_id), '') IS NOT NULL
  AND NULLIF(TRIM(o.order_purchase_timestamp), '') IS NOT NULL
ON CONFLICT (order_id) DO NOTHING;

COMMIT;
