-- staging.stg_products
-- Technique: LEFT JOIN translation, CAST, corrected column names
BEGIN;

TRUNCATE staging.stg_products CASCADE;

INSERT INTO staging.stg_products (
    product_id,
    product_category_name,
    product_category_name_english,
    product_name_length,
    product_description_length,
    product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm
)
SELECT DISTINCT ON (TRIM(p.product_id))
    TRIM(p.product_id)                                                      AS product_id,
    NULLIF(TRIM(p.product_category_name), '')                               AS product_category_name,
    COALESCE(t.product_category_name_english, NULLIF(TRIM(p.product_category_name), ''))
                                                                            AS product_category_name_english,
    NULLIF(TRIM(p.product_name_lenght), '')::INTEGER                        AS product_name_length,
    NULLIF(TRIM(p.product_description_lenght), '')::INTEGER                 AS product_description_length,
    NULLIF(TRIM(p.product_photos_qty), '')::INTEGER                         AS product_photos_qty,
    NULLIF(TRIM(p.product_weight_g), '')::NUMERIC(12, 2)                    AS product_weight_g,
    NULLIF(TRIM(p.product_length_cm), '')::NUMERIC(12, 2)                   AS product_length_cm,
    NULLIF(TRIM(p.product_height_cm), '')::NUMERIC(12, 2)                   AS product_height_cm,
    NULLIF(TRIM(p.product_width_cm), '')::NUMERIC(12, 2)                    AS product_width_cm
FROM raw.olist_products p
LEFT JOIN staging.stg_product_category_translation t
    ON t.product_category_name = NULLIF(TRIM(p.product_category_name), '')
WHERE NULLIF(TRIM(p.product_id), '') IS NOT NULL
ORDER BY TRIM(p.product_id);

COMMIT;
