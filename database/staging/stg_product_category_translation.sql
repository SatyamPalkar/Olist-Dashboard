-- staging.stg_product_category_translation
-- Technique: DISTINCT, TRIM, NULLIF
BEGIN;

TRUNCATE staging.stg_product_category_translation;

INSERT INTO staging.stg_product_category_translation (
    product_category_name,
    product_category_name_english
)
SELECT DISTINCT
    TRIM(product_category_name)                 AS product_category_name,
    TRIM(product_category_name_english)         AS product_category_name_english
FROM raw.product_category_name_translation
WHERE NULLIF(TRIM(product_category_name), '') IS NOT NULL
  AND NULLIF(TRIM(product_category_name_english), '') IS NOT NULL;

COMMIT;
