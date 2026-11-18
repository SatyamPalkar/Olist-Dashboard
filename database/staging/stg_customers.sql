-- staging.stg_customers
-- Technique: TRIM, LPAD, CASE-free normalisation
BEGIN;

TRUNCATE staging.stg_customers CASCADE;

INSERT INTO staging.stg_customers (
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state
)
SELECT DISTINCT ON (TRIM(customer_id))
    TRIM(customer_id)                                                       AS customer_id,
    TRIM(customer_unique_id)                                                AS customer_unique_id,
    LPAD(REGEXP_REPLACE(TRIM(customer_zip_code_prefix), '[^0-9]', '', 'g'), 5, '0')
                                                                            AS customer_zip_code_prefix,
    LOWER(TRIM(customer_city))                                              AS customer_city,
    UPPER(TRIM(customer_state))                                             AS customer_state
FROM raw.olist_customers
WHERE NULLIF(TRIM(customer_id), '') IS NOT NULL
  AND NULLIF(TRIM(customer_unique_id), '') IS NOT NULL
ORDER BY TRIM(customer_id), TRIM(customer_unique_id);

COMMIT;
