-- staging.stg_order_payments
BEGIN;

TRUNCATE staging.stg_order_payments CASCADE;

INSERT INTO staging.stg_order_payments (
    order_id,
    payment_sequential,
    payment_type,
    payment_installments,
    payment_value
)
SELECT
    TRIM(p.order_id)                                                        AS order_id,
    TRIM(p.payment_sequential)::INTEGER                                     AS payment_sequential,
    LOWER(TRIM(p.payment_type))                                             AS payment_type,
    COALESCE(NULLIF(TRIM(p.payment_installments), '')::INTEGER, 0)          AS payment_installments,
    TRIM(p.payment_value)::NUMERIC(12, 2)                                   AS payment_value
FROM raw.olist_order_payments p
WHERE NULLIF(TRIM(p.order_id), '') IS NOT NULL
  AND NULLIF(TRIM(p.payment_sequential), '') IS NOT NULL
  AND NULLIF(TRIM(p.payment_value), '') IS NOT NULL
ON CONFLICT (order_id, payment_sequential) DO NOTHING;

COMMIT;
