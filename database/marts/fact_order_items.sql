-- analytics.fact_order_items
-- Grain: order_id + order_item_id
-- Canonical fact for product / seller / category revenue (price = merchandise sales)
BEGIN;

TRUNCATE analytics.fact_order_items RESTART IDENTITY CASCADE;

INSERT INTO analytics.fact_order_items (
    order_id,
    order_item_id,
    order_key,
    product_key,
    seller_key,
    customer_key,
    purchase_date_key,
    customer_geography_key,
    seller_geography_key,
    shipping_limit_date,
    price,
    freight_value,
    item_total
)
SELECT
    i.order_id,
    i.order_item_id,
    fo.order_key,
    COALESCE(
        dp.product_key,
        (SELECT product_key FROM analytics.dim_products WHERE product_id = '__UNKNOWN__')
    )                                                   AS product_key,
    COALESCE(
        ds.seller_key,
        (SELECT seller_key FROM analytics.dim_sellers WHERE seller_id = '__UNKNOWN__')
    )                                                   AS seller_key,
    fo.customer_key,
    fo.purchase_date_key,
    fo.customer_geography_key,
    ds.geography_key                                    AS seller_geography_key,
    i.shipping_limit_date,
    i.price,
    i.freight_value,
    i.item_total
FROM staging.stg_order_items i
JOIN analytics.fact_orders fo
    ON fo.order_id = i.order_id
LEFT JOIN analytics.dim_products dp
    ON dp.product_id = i.product_id
LEFT JOIN analytics.dim_sellers ds
    ON ds.seller_id = i.seller_id;

COMMIT;
