-- =============================================================================
-- Indexes — justified for Power BI filters and aggregation paths.
-- Safe to re-run.
-- =============================================================================
BEGIN;

-- Staging lookup helpers (mart builds)
CREATE INDEX IF NOT EXISTS ix_stg_customers_unique_id
    ON staging.stg_customers (customer_unique_id);

CREATE INDEX IF NOT EXISTS ix_stg_orders_customer_id
    ON staging.stg_orders (customer_id);

CREATE INDEX IF NOT EXISTS ix_stg_orders_purchase_date
    ON staging.stg_orders (purchase_date);

CREATE INDEX IF NOT EXISTS ix_stg_order_items_product
    ON staging.stg_order_items (product_id);

CREATE INDEX IF NOT EXISTS ix_stg_order_items_seller
    ON staging.stg_order_items (seller_id);

CREATE INDEX IF NOT EXISTS ix_stg_order_payments_order
    ON staging.stg_order_payments (order_id);

CREATE INDEX IF NOT EXISTS ix_stg_order_reviews_order
    ON staging.stg_order_reviews (order_id);

-- Fact filter / join paths
CREATE INDEX IF NOT EXISTS ix_fact_orders_purchase_date
    ON analytics.fact_orders (purchase_date_key);

CREATE INDEX IF NOT EXISTS ix_fact_orders_customer
    ON analytics.fact_orders (customer_key);

CREATE INDEX IF NOT EXISTS ix_fact_orders_status
    ON analytics.fact_orders (order_status);

CREATE INDEX IF NOT EXISTS ix_fact_orders_customer_geo
    ON analytics.fact_orders (customer_geography_key);

CREATE INDEX IF NOT EXISTS ix_fact_oi_purchase_date
    ON analytics.fact_order_items (purchase_date_key);

CREATE INDEX IF NOT EXISTS ix_fact_oi_product
    ON analytics.fact_order_items (product_key);

CREATE INDEX IF NOT EXISTS ix_fact_oi_seller
    ON analytics.fact_order_items (seller_key);

CREATE INDEX IF NOT EXISTS ix_fact_oi_customer
    ON analytics.fact_order_items (customer_key);

CREATE INDEX IF NOT EXISTS ix_fact_oi_customer_geo
    ON analytics.fact_order_items (customer_geography_key);

CREATE INDEX IF NOT EXISTS ix_fact_payments_type
    ON analytics.fact_payments (payment_type);

CREATE INDEX IF NOT EXISTS ix_fact_payments_purchase_date
    ON analytics.fact_payments (purchase_date_key);

CREATE INDEX IF NOT EXISTS ix_fact_reviews_score
    ON analytics.fact_order_reviews (review_score);

CREATE INDEX IF NOT EXISTS ix_fact_reviews_purchase_date
    ON analytics.fact_order_reviews (purchase_date_key);

-- Dimension attribute search
CREATE INDEX IF NOT EXISTS ix_dim_products_category_en
    ON analytics.dim_products (product_category_name_english);

CREATE INDEX IF NOT EXISTS ix_dim_geography_state
    ON analytics.dim_geography (state);

CREATE INDEX IF NOT EXISTS ix_dim_customers_state
    ON analytics.dim_customers (state);

CREATE INDEX IF NOT EXISTS ix_dim_date_year_month
    ON analytics.dim_date (year_month);

COMMIT;
