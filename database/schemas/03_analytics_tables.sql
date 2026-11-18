-- =============================================================================
-- ANALYTICS layer DDL — star schema (dimensions + facts).
-- Surrogate keys for Power BI relationships.
-- Safe to re-run.
-- =============================================================================
BEGIN;

-- Drop facts before dimensions (FK dependency)
DROP TABLE IF EXISTS analytics.fact_order_reviews CASCADE;
DROP TABLE IF EXISTS analytics.fact_payments CASCADE;
DROP TABLE IF EXISTS analytics.fact_order_items CASCADE;
DROP TABLE IF EXISTS analytics.fact_orders CASCADE;
DROP TABLE IF EXISTS analytics.dim_customers CASCADE;
DROP TABLE IF EXISTS analytics.dim_products CASCADE;
DROP TABLE IF EXISTS analytics.dim_sellers CASCADE;
DROP TABLE IF EXISTS analytics.dim_geography CASCADE;
DROP TABLE IF EXISTS analytics.dim_date CASCADE;

-- =============================================================================
-- DIMENSIONS
-- =============================================================================

-- ---------------------------------------------------------------------------
-- dim_date
-- Grain: one calendar day. Generated (not from source).
-- ---------------------------------------------------------------------------
CREATE TABLE analytics.dim_date (
    date_key            INTEGER     NOT NULL,   -- YYYYMMDD
    full_date           DATE        NOT NULL,
    year                SMALLINT    NOT NULL,
    quarter             SMALLINT    NOT NULL,
    month               SMALLINT    NOT NULL,
    month_name          TEXT        NOT NULL,
    month_name_short    TEXT        NOT NULL,
    day_of_month        SMALLINT    NOT NULL,
    day_of_week         SMALLINT    NOT NULL,   -- ISO: 1=Mon … 7=Sun
    day_name            TEXT        NOT NULL,
    week_of_year        SMALLINT    NOT NULL,
    year_month          TEXT        NOT NULL,   -- YYYY-MM
    is_weekend          BOOLEAN     NOT NULL,
    CONSTRAINT pk_dim_date PRIMARY KEY (date_key),
    CONSTRAINT uq_dim_date_full_date UNIQUE (full_date)
);
COMMENT ON TABLE analytics.dim_date IS 'Date dimension. Grain: one day. date_key = YYYYMMDD.';

-- ---------------------------------------------------------------------------
-- dim_geography
-- Grain: one zip_code_prefix (customer/seller location key).
-- ---------------------------------------------------------------------------
CREATE TABLE analytics.dim_geography (
    geography_key       BIGSERIAL   NOT NULL,
    zip_code_prefix     TEXT        NOT NULL,
    city                TEXT,
    state               TEXT,
    state_name          TEXT,
    region              TEXT,                   -- N/NE/SE/S/CW (Brazil)
    latitude            NUMERIC(12, 8),
    longitude           NUMERIC(12, 8),
    CONSTRAINT pk_dim_geography PRIMARY KEY (geography_key),
    CONSTRAINT uq_dim_geography_zip UNIQUE (zip_code_prefix)
);
COMMENT ON TABLE analytics.dim_geography IS 'Geography dimension. Grain: zip_code_prefix. SCD Type 1.';

-- ---------------------------------------------------------------------------
-- dim_customers
-- Grain: one unique customer (customer_unique_id). SCD Type 1.
-- Attributes taken from the most recent order-linked customer_id row.
-- ---------------------------------------------------------------------------
CREATE TABLE analytics.dim_customers (
    customer_key            BIGSERIAL   NOT NULL,
    customer_unique_id      TEXT        NOT NULL,
    geography_key           BIGINT,
    zip_code_prefix         TEXT,
    city                    TEXT,
    state                   TEXT,
    first_order_date        DATE,
    last_order_date         DATE,
    order_count             INTEGER     NOT NULL DEFAULT 0,
    is_repeat_customer      BOOLEAN     NOT NULL DEFAULT FALSE,
    CONSTRAINT pk_dim_customers PRIMARY KEY (customer_key),
    CONSTRAINT uq_dim_customers_unique_id UNIQUE (customer_unique_id),
    CONSTRAINT fk_dim_customers_geography
        FOREIGN KEY (geography_key) REFERENCES analytics.dim_geography (geography_key)
);
COMMENT ON TABLE analytics.dim_customers IS
    'Customer dimension keyed on customer_unique_id (NOT customer_id). SCD Type 1.';

-- ---------------------------------------------------------------------------
-- dim_products
-- Grain: one product_id. SCD Type 1.
-- ---------------------------------------------------------------------------
CREATE TABLE analytics.dim_products (
    product_key                     BIGSERIAL       NOT NULL,
    product_id                      TEXT            NOT NULL,
    product_category_name           TEXT,
    product_category_name_english   TEXT,
    product_name_length             INTEGER,
    product_description_length      INTEGER,
    product_photos_qty              INTEGER,
    product_weight_g                NUMERIC(12, 2),
    product_length_cm               NUMERIC(12, 2),
    product_height_cm               NUMERIC(12, 2),
    product_width_cm                NUMERIC(12, 2),
    CONSTRAINT pk_dim_products PRIMARY KEY (product_key),
    CONSTRAINT uq_dim_products_product_id UNIQUE (product_id)
);
COMMENT ON TABLE analytics.dim_products IS 'Product dimension. Grain: product_id. SCD Type 1.';

-- ---------------------------------------------------------------------------
-- dim_sellers
-- Grain: one seller_id. SCD Type 1.
-- ---------------------------------------------------------------------------
CREATE TABLE analytics.dim_sellers (
    seller_key          BIGSERIAL   NOT NULL,
    seller_id           TEXT        NOT NULL,
    geography_key       BIGINT,
    zip_code_prefix     TEXT,
    city                TEXT,
    state               TEXT,
    CONSTRAINT pk_dim_sellers PRIMARY KEY (seller_key),
    CONSTRAINT uq_dim_sellers_seller_id UNIQUE (seller_id),
    CONSTRAINT fk_dim_sellers_geography
        FOREIGN KEY (geography_key) REFERENCES analytics.dim_geography (geography_key)
);
COMMENT ON TABLE analytics.dim_sellers IS 'Seller dimension. Grain: seller_id. SCD Type 1.';

-- =============================================================================
-- FACTS
-- =============================================================================

-- ---------------------------------------------------------------------------
-- fact_orders
-- Grain: one row per order (order_id).
-- Monetary measures are PRE-AGGREGATED from items/payments to avoid fan-out.
-- ---------------------------------------------------------------------------
CREATE TABLE analytics.fact_orders (
    order_key                       BIGSERIAL       NOT NULL,
    order_id                        TEXT            NOT NULL,
    customer_key                    BIGINT          NOT NULL,
    customer_geography_key          BIGINT,
    purchase_date_key               INTEGER         NOT NULL,
    approved_date_key               INTEGER,
    delivered_customer_date_key     INTEGER,
    estimated_delivery_date_key     INTEGER,
    order_status                    TEXT            NOT NULL,
    is_delivered                    BOOLEAN         NOT NULL,
    is_canceled                     BOOLEAN         NOT NULL,
    -- Measures (order grain — no double counting)
    merchandise_sales               NUMERIC(14, 2)  NOT NULL DEFAULT 0,  -- SUM(price)
    freight_charges                 NUMERIC(14, 2)  NOT NULL DEFAULT 0,  -- SUM(freight_value)
    order_value                     NUMERIC(14, 2)  NOT NULL DEFAULT 0,  -- merchandise + freight
    payment_amount                  NUMERIC(14, 2)  NOT NULL DEFAULT 0,  -- SUM(payment_value)
    item_count                      INTEGER         NOT NULL DEFAULT 0,
    payment_count                   INTEGER         NOT NULL DEFAULT 0,
    delivery_days                   NUMERIC(10, 2),
    is_late_delivery                BOOLEAN,
    review_score                    SMALLINT,                           -- latest/primary review if any
    CONSTRAINT pk_fact_orders PRIMARY KEY (order_key),
    CONSTRAINT uq_fact_orders_order_id UNIQUE (order_id),
    CONSTRAINT fk_fact_orders_customer
        FOREIGN KEY (customer_key) REFERENCES analytics.dim_customers (customer_key),
    CONSTRAINT fk_fact_orders_customer_geo
        FOREIGN KEY (customer_geography_key) REFERENCES analytics.dim_geography (geography_key),
    CONSTRAINT fk_fact_orders_purchase_date
        FOREIGN KEY (purchase_date_key) REFERENCES analytics.dim_date (date_key)
);
COMMENT ON TABLE analytics.fact_orders IS
    'Order fact. Grain: one order. merchandise_sales ≠ payment_amount; profit is NOT available (no COGS).';
COMMENT ON COLUMN analytics.fact_orders.merchandise_sales IS 'SUM(order_items.price) — product revenue excl. freight.';
COMMENT ON COLUMN analytics.fact_orders.freight_charges IS 'SUM(order_items.freight_value).';
COMMENT ON COLUMN analytics.fact_orders.order_value IS 'merchandise_sales + freight_charges (GMV at order grain).';
COMMENT ON COLUMN analytics.fact_orders.payment_amount IS 'SUM(payments.payment_value). May differ from order_value (vouchers/splits).';

-- ---------------------------------------------------------------------------
-- fact_order_items
-- Grain: one row per order line (order_id + order_item_id).
-- Primary fact for product/seller/category revenue analysis.
-- ---------------------------------------------------------------------------
CREATE TABLE analytics.fact_order_items (
    order_item_key          BIGSERIAL       NOT NULL,
    order_id                TEXT            NOT NULL,
    order_item_id           INTEGER         NOT NULL,
    order_key               BIGINT          NOT NULL,
    product_key             BIGINT          NOT NULL,
    seller_key              BIGINT          NOT NULL,
    customer_key            BIGINT          NOT NULL,
    purchase_date_key       INTEGER         NOT NULL,
    customer_geography_key  BIGINT,
    seller_geography_key    BIGINT,
    shipping_limit_date     TIMESTAMP,
    -- Measures
    price                   NUMERIC(12, 2)  NOT NULL,  -- merchandise sales (line)
    freight_value           NUMERIC(12, 2)  NOT NULL,  -- freight (line)
    item_total              NUMERIC(12, 2)  NOT NULL,  -- price + freight
    CONSTRAINT pk_fact_order_items PRIMARY KEY (order_item_key),
    CONSTRAINT uq_fact_order_items UNIQUE (order_id, order_item_id),
    CONSTRAINT fk_fact_oi_order
        FOREIGN KEY (order_key) REFERENCES analytics.fact_orders (order_key),
    CONSTRAINT fk_fact_oi_product
        FOREIGN KEY (product_key) REFERENCES analytics.dim_products (product_key),
    CONSTRAINT fk_fact_oi_seller
        FOREIGN KEY (seller_key) REFERENCES analytics.dim_sellers (seller_key),
    CONSTRAINT fk_fact_oi_customer
        FOREIGN KEY (customer_key) REFERENCES analytics.dim_customers (customer_key),
    CONSTRAINT fk_fact_oi_purchase_date
        FOREIGN KEY (purchase_date_key) REFERENCES analytics.dim_date (date_key)
);
COMMENT ON TABLE analytics.fact_order_items IS
    'Order-item fact. Grain: order_id + order_item_id. Use for product/seller revenue. Do NOT join to payments at this grain.';
COMMENT ON COLUMN analytics.fact_order_items.price IS 'Line merchandise sales (excl. freight). Canonical revenue measure.';

-- ---------------------------------------------------------------------------
-- fact_payments
-- Grain: one row per payment (order_id + payment_sequential).
-- ---------------------------------------------------------------------------
CREATE TABLE analytics.fact_payments (
    payment_key             BIGSERIAL       NOT NULL,
    order_id                TEXT            NOT NULL,
    payment_sequential      INTEGER         NOT NULL,
    order_key               BIGINT          NOT NULL,
    customer_key            BIGINT          NOT NULL,
    purchase_date_key       INTEGER         NOT NULL,
    payment_type            TEXT            NOT NULL,
    payment_installments    INTEGER         NOT NULL,
    payment_value           NUMERIC(12, 2)  NOT NULL,
    CONSTRAINT pk_fact_payments PRIMARY KEY (payment_key),
    CONSTRAINT uq_fact_payments UNIQUE (order_id, payment_sequential),
    CONSTRAINT fk_fact_pay_order
        FOREIGN KEY (order_key) REFERENCES analytics.fact_orders (order_key),
    CONSTRAINT fk_fact_pay_customer
        FOREIGN KEY (customer_key) REFERENCES analytics.dim_customers (customer_key),
    CONSTRAINT fk_fact_pay_purchase_date
        FOREIGN KEY (purchase_date_key) REFERENCES analytics.dim_date (date_key)
);
COMMENT ON TABLE analytics.fact_payments IS
    'Payment fact. Grain: order_id + payment_sequential. Do NOT join to order_items without pre-aggregation.';

-- ---------------------------------------------------------------------------
-- fact_order_reviews
-- Grain: one row per review surrogate (review_sk from staging).
-- ---------------------------------------------------------------------------
CREATE TABLE analytics.fact_order_reviews (
    review_key              BIGSERIAL       NOT NULL,
    review_id               TEXT            NOT NULL,
    order_id                TEXT            NOT NULL,
    order_key               BIGINT          NOT NULL,
    customer_key            BIGINT          NOT NULL,
    purchase_date_key       INTEGER         NOT NULL,
    review_creation_date_key INTEGER,
    review_score            SMALLINT        NOT NULL,
    has_comment             BOOLEAN         NOT NULL,
    review_comment_title    TEXT,
    review_comment_message  TEXT,
    review_answer_timestamp TIMESTAMP,
    CONSTRAINT pk_fact_order_reviews PRIMARY KEY (review_key),
    CONSTRAINT fk_fact_rev_order
        FOREIGN KEY (order_key) REFERENCES analytics.fact_orders (order_key),
    CONSTRAINT fk_fact_rev_customer
        FOREIGN KEY (customer_key) REFERENCES analytics.dim_customers (customer_key),
    CONSTRAINT fk_fact_rev_purchase_date
        FOREIGN KEY (purchase_date_key) REFERENCES analytics.dim_date (date_key),
    CONSTRAINT chk_fact_review_score CHECK (review_score BETWEEN 1 AND 5)
);
COMMENT ON TABLE analytics.fact_order_reviews IS
    'Review fact. Grain: one review row (surrogate). Scores 1–5.';

COMMIT;
