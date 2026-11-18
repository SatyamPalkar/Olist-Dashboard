-- staging.stg_sellers
BEGIN;

TRUNCATE staging.stg_sellers CASCADE;

INSERT INTO staging.stg_sellers (
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state
)
SELECT DISTINCT ON (TRIM(seller_id))
    TRIM(seller_id)                                                         AS seller_id,
    LPAD(REGEXP_REPLACE(TRIM(seller_zip_code_prefix), '[^0-9]', '', 'g'), 5, '0')
                                                                            AS seller_zip_code_prefix,
    LOWER(TRIM(seller_city))                                                AS seller_city,
    UPPER(TRIM(seller_state))                                               AS seller_state
FROM raw.olist_sellers
WHERE NULLIF(TRIM(seller_id), '') IS NOT NULL
ORDER BY TRIM(seller_id);

COMMIT;
