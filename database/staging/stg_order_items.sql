-- staging.stg_order_items
-- Technique: CAST numerics, computed item_total
BEGIN;

TRUNCATE staging.stg_order_items CASCADE;

INSERT INTO staging.stg_order_items (
    order_id,
    order_item_id,
    product_id,
    seller_id,
    shipping_limit_date,
    price,
    freight_value,
    item_total
)
SELECT
    TRIM(i.order_id)                                                        AS order_id,
    TRIM(i.order_item_id)::INTEGER                                          AS order_item_id,
    TRIM(i.product_id)                                                      AS product_id,
    TRIM(i.seller_id)                                                       AS seller_id,
    NULLIF(TRIM(i.shipping_limit_date), '')::TIMESTAMP                      AS shipping_limit_date,
    TRIM(i.price)::NUMERIC(12, 2)                                           AS price,
    TRIM(i.freight_value)::NUMERIC(12, 2)                                   AS freight_value,
    (TRIM(i.price)::NUMERIC(12, 2) + TRIM(i.freight_value)::NUMERIC(12, 2)) AS item_total
FROM raw.olist_order_items i
WHERE NULLIF(TRIM(i.order_id), '') IS NOT NULL
  AND NULLIF(TRIM(i.order_item_id), '') IS NOT NULL
  AND NULLIF(TRIM(i.product_id), '') IS NOT NULL
  AND NULLIF(TRIM(i.seller_id), '') IS NOT NULL
  AND NULLIF(TRIM(i.price), '') IS NOT NULL
  AND NULLIF(TRIM(i.freight_value), '') IS NOT NULL
ON CONFLICT (order_id, order_item_id) DO NOTHING;

COMMIT;
