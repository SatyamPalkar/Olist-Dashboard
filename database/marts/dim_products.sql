-- analytics.dim_products
BEGIN;

TRUNCATE analytics.dim_products RESTART IDENTITY CASCADE;

INSERT INTO analytics.dim_products (
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
SELECT
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
FROM staging.stg_products;

-- Unknown product placeholder for orphaned order items
INSERT INTO analytics.dim_products (
    product_id,
    product_category_name,
    product_category_name_english
)
VALUES ('__UNKNOWN__', 'unknown', 'unknown')
ON CONFLICT (product_id) DO NOTHING;

COMMIT;
