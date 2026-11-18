-- =============================================================================
-- STAGING layer DDL — typed, cleaned business entities.
-- Populated by database/staging/*.sql transforms.
-- Safe to re-run.
-- =============================================================================
BEGIN;

DROP TABLE IF EXISTS staging.stg_orders CASCADE;
DROP TABLE IF EXISTS staging.stg_order_items CASCADE;
DROP TABLE IF EXISTS staging.stg_order_payments CASCADE;
DROP TABLE IF EXISTS staging.stg_order_reviews CASCADE;
DROP TABLE IF EXISTS staging.stg_customers CASCADE;
DROP TABLE IF EXISTS staging.stg_products CASCADE;
DROP TABLE IF EXISTS staging.stg_sellers CASCADE;
DROP TABLE IF EXISTS staging.stg_geolocation CASCADE;
DROP TABLE IF EXISTS staging.stg_product_category_translation CASCADE;

CREATE TABLE staging.stg_orders (
    order_id                        TEXT        NOT NULL,
    customer_id                     TEXT        NOT NULL,
    order_status                    TEXT        NOT NULL,
    order_purchase_timestamp        TIMESTAMP   NOT NULL,
    order_approved_at               TIMESTAMP,
    order_delivered_carrier_date    TIMESTAMP,
    order_delivered_customer_date   TIMESTAMP,
    order_estimated_delivery_date   TIMESTAMP,
    purchase_date                   DATE        NOT NULL,
    is_delivered                    BOOLEAN     NOT NULL,
    is_canceled                     BOOLEAN     NOT NULL,
    delivery_days                   NUMERIC(10, 2),
    is_late_delivery                BOOLEAN,
    _loaded_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_stg_orders PRIMARY KEY (order_id)
);
COMMENT ON TABLE staging.stg_orders IS 'Cleaned orders. One row per order_id.';

CREATE TABLE staging.stg_order_items (
    order_id                TEXT            NOT NULL,
    order_item_id           INTEGER         NOT NULL,
    product_id              TEXT            NOT NULL,
    seller_id               TEXT            NOT NULL,
    shipping_limit_date     TIMESTAMP,
    price                   NUMERIC(12, 2)  NOT NULL,
    freight_value           NUMERIC(12, 2)  NOT NULL,
    item_total              NUMERIC(12, 2)  NOT NULL,  -- price + freight
    _loaded_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_stg_order_items PRIMARY KEY (order_id, order_item_id)
);
COMMENT ON TABLE staging.stg_order_items IS 'Cleaned order lines. Grain: order_id + order_item_id.';

CREATE TABLE staging.stg_order_payments (
    order_id                TEXT            NOT NULL,
    payment_sequential      INTEGER         NOT NULL,
    payment_type            TEXT            NOT NULL,
    payment_installments    INTEGER         NOT NULL,
    payment_value           NUMERIC(12, 2)  NOT NULL,
    _loaded_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_stg_order_payments PRIMARY KEY (order_id, payment_sequential)
);
COMMENT ON TABLE staging.stg_order_payments IS 'Cleaned payments. Grain: order_id + payment_sequential.';

CREATE TABLE staging.stg_order_reviews (
    review_sk                   BIGSERIAL,
    review_id                   TEXT            NOT NULL,
    order_id                    TEXT            NOT NULL,
    review_score                SMALLINT        NOT NULL,
    review_comment_title        TEXT,
    review_comment_message      TEXT,
    review_creation_date        TIMESTAMP,
    review_answer_timestamp     TIMESTAMP,
    has_comment                 BOOLEAN         NOT NULL,
    _loaded_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_stg_order_reviews PRIMARY KEY (review_sk),
    CONSTRAINT chk_stg_review_score CHECK (review_score BETWEEN 1 AND 5)
);
COMMENT ON TABLE staging.stg_order_reviews IS 'Cleaned reviews. Surrogate PK because source review_id is not reliably unique.';

CREATE TABLE staging.stg_customers (
    customer_id                 TEXT        NOT NULL,
    customer_unique_id          TEXT        NOT NULL,
    customer_zip_code_prefix    TEXT        NOT NULL,
    customer_city               TEXT        NOT NULL,
    customer_state              TEXT        NOT NULL,
    _loaded_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_stg_customers PRIMARY KEY (customer_id)
);
COMMENT ON TABLE staging.stg_customers IS 'Order-level customer keys + unique customer identity.';

CREATE TABLE staging.stg_products (
    product_id                      TEXT            NOT NULL,
    product_category_name           TEXT,
    product_category_name_english   TEXT,
    product_name_length             INTEGER,        -- corrected spelling
    product_description_length      INTEGER,
    product_photos_qty              INTEGER,
    product_weight_g                NUMERIC(12, 2),
    product_length_cm               NUMERIC(12, 2),
    product_height_cm               NUMERIC(12, 2),
    product_width_cm                NUMERIC(12, 2),
    _loaded_at                      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_stg_products PRIMARY KEY (product_id)
);
COMMENT ON TABLE staging.stg_products IS 'Products with English category when available.';

CREATE TABLE staging.stg_sellers (
    seller_id                   TEXT        NOT NULL,
    seller_zip_code_prefix      TEXT        NOT NULL,
    seller_city                 TEXT        NOT NULL,
    seller_state                TEXT        NOT NULL,
    _loaded_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_stg_sellers PRIMARY KEY (seller_id)
);
COMMENT ON TABLE staging.stg_sellers IS 'Cleaned sellers.';

CREATE TABLE staging.stg_geolocation (
    zip_code_prefix     TEXT            NOT NULL,
    avg_lat             NUMERIC(12, 8)  NOT NULL,
    avg_lng             NUMERIC(12, 8)  NOT NULL,
    city                TEXT,
    state               TEXT,
    point_count         INTEGER         NOT NULL,
    _loaded_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_stg_geolocation PRIMARY KEY (zip_code_prefix)
);
COMMENT ON TABLE staging.stg_geolocation IS 'One row per zip_code_prefix (averaged lat/lng).';

CREATE TABLE staging.stg_product_category_translation (
    product_category_name           TEXT        NOT NULL,
    product_category_name_english   TEXT        NOT NULL,
    _loaded_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_stg_category_translation PRIMARY KEY (product_category_name)
);
COMMENT ON TABLE staging.stg_product_category_translation IS 'PT → EN product category map.';

COMMIT;
