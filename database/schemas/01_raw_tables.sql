-- =============================================================================
-- RAW layer DDL — mirrors Olist CSV contracts (TEXT-heavy for safe load).
-- Contract: docs/contracts_raw_staging.md
-- Data Engineer loads CSVs into these tables (COPY / ETL).
-- Safe to re-run: drops and recreates raw tables.
-- =============================================================================
BEGIN;

DROP TABLE IF EXISTS raw.olist_orders CASCADE;
DROP TABLE IF EXISTS raw.olist_order_items CASCADE;
DROP TABLE IF EXISTS raw.olist_order_payments CASCADE;
DROP TABLE IF EXISTS raw.olist_order_reviews CASCADE;
DROP TABLE IF EXISTS raw.olist_customers CASCADE;
DROP TABLE IF EXISTS raw.olist_products CASCADE;
DROP TABLE IF EXISTS raw.olist_sellers CASCADE;
DROP TABLE IF EXISTS raw.olist_geolocation CASCADE;
DROP TABLE IF EXISTS raw.product_category_name_translation CASCADE;

-- ---------------------------------------------------------------------------
-- olist_orders_dataset.csv
-- ---------------------------------------------------------------------------
CREATE TABLE raw.olist_orders (
    order_id                        TEXT,
    customer_id                     TEXT,
    order_status                    TEXT,
    order_purchase_timestamp        TEXT,
    order_approved_at               TEXT,
    order_delivered_carrier_date    TEXT,
    order_delivered_customer_date   TEXT,
    order_estimated_delivery_date   TEXT,
    _loaded_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE raw.olist_orders IS 'Source: olist_orders_dataset.csv — one row per order.';

-- ---------------------------------------------------------------------------
-- olist_order_items_dataset.csv
-- ---------------------------------------------------------------------------
CREATE TABLE raw.olist_order_items (
    order_id                TEXT,
    order_item_id           TEXT,
    product_id              TEXT,
    seller_id               TEXT,
    shipping_limit_date     TEXT,
    price                   TEXT,
    freight_value           TEXT,
    _loaded_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE raw.olist_order_items IS 'Source: olist_order_items_dataset.csv — grain: order_id + order_item_id.';

-- ---------------------------------------------------------------------------
-- olist_order_payments_dataset.csv
-- ---------------------------------------------------------------------------
CREATE TABLE raw.olist_order_payments (
    order_id                TEXT,
    payment_sequential      TEXT,
    payment_type            TEXT,
    payment_installments    TEXT,
    payment_value           TEXT,
    _loaded_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE raw.olist_order_payments IS 'Source: olist_order_payments_dataset.csv — grain: order_id + payment_sequential.';

-- ---------------------------------------------------------------------------
-- olist_order_reviews_dataset.csv
-- ---------------------------------------------------------------------------
CREATE TABLE raw.olist_order_reviews (
    review_id                   TEXT,
    order_id                    TEXT,
    review_score                TEXT,
    review_comment_title        TEXT,
    review_comment_message      TEXT,
    review_creation_date        TEXT,
    review_answer_timestamp     TEXT,
    _loaded_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE raw.olist_order_reviews IS 'Source: olist_order_reviews_dataset.csv. Note: review_id is not always unique in the public dump.';

-- ---------------------------------------------------------------------------
-- olist_customers_dataset.csv
-- ---------------------------------------------------------------------------
CREATE TABLE raw.olist_customers (
    customer_id                 TEXT,
    customer_unique_id          TEXT,
    customer_zip_code_prefix    TEXT,
    customer_city               TEXT,
    customer_state              TEXT,
    _loaded_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE raw.olist_customers IS 'Source: olist_customers_dataset.csv. customer_id is per-order; customer_unique_id is the person.';

-- ---------------------------------------------------------------------------
-- olist_products_dataset.csv
-- ---------------------------------------------------------------------------
CREATE TABLE raw.olist_products (
    product_id                      TEXT,
    product_category_name           TEXT,
    product_name_lenght             TEXT,  -- source spelling (lenght)
    product_description_lenght      TEXT,  -- source spelling (lenght)
    product_photos_qty              TEXT,
    product_weight_g                TEXT,
    product_length_cm               TEXT,
    product_height_cm               TEXT,
    product_width_cm                TEXT,
    _loaded_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE raw.olist_products IS 'Source: olist_products_dataset.csv. Preserves source column spelling lenght.';

-- ---------------------------------------------------------------------------
-- olist_sellers_dataset.csv
-- ---------------------------------------------------------------------------
CREATE TABLE raw.olist_sellers (
    seller_id                   TEXT,
    seller_zip_code_prefix      TEXT,
    seller_city                 TEXT,
    seller_state                TEXT,
    _loaded_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE raw.olist_sellers IS 'Source: olist_sellers_dataset.csv.';

-- ---------------------------------------------------------------------------
-- olist_geolocation_dataset.csv
-- ---------------------------------------------------------------------------
CREATE TABLE raw.olist_geolocation (
    geolocation_zip_code_prefix TEXT,
    geolocation_lat             TEXT,
    geolocation_lng             TEXT,
    geolocation_city            TEXT,
    geolocation_state           TEXT,
    _loaded_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE raw.olist_geolocation IS 'Source: olist_geolocation_dataset.csv. Many rows per zip_code_prefix.';

-- ---------------------------------------------------------------------------
-- product_category_name_translation.csv
-- ---------------------------------------------------------------------------
CREATE TABLE raw.product_category_name_translation (
    product_category_name           TEXT,
    product_category_name_english   TEXT,
    _loaded_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE raw.product_category_name_translation IS 'Source: product_category_name_translation.csv — PT → EN category map.';

COMMIT;
