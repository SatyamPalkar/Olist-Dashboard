-- analytics.fact_payments
-- Grain: order_id + payment_sequential
BEGIN;

TRUNCATE analytics.fact_payments RESTART IDENTITY CASCADE;

INSERT INTO analytics.fact_payments (
    order_id,
    payment_sequential,
    order_key,
    customer_key,
    purchase_date_key,
    payment_type,
    payment_installments,
    payment_value
)
SELECT
    p.order_id,
    p.payment_sequential,
    fo.order_key,
    fo.customer_key,
    fo.purchase_date_key,
    p.payment_type,
    p.payment_installments,
    p.payment_value
FROM staging.stg_order_payments p
JOIN analytics.fact_orders fo
    ON fo.order_id = p.order_id;

COMMIT;
