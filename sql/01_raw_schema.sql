-- =============================================================================
-- Raw schema for Olist e-commerce ingestion
-- Contract for SQL Architect coordination: landing zone mirrors source CSVs
-- with standardised column names, lineage metadata, and no business KPIs.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS etl;

-- Ingestion audit / reconciliation
CREATE TABLE IF NOT EXISTS etl.ingestion_runs (
    run_id              UUID PRIMARY KEY,
    pipeline_name       TEXT NOT NULL,
    started_at          TIMESTAMPTZ NOT NULL,
    finished_at         TIMESTAMPTZ,
    status              TEXT NOT NULL DEFAULT 'running',
    source_directory    TEXT,
    notes               TEXT
);

CREATE TABLE IF NOT EXISTS etl.ingestion_file_stats (
    run_id              UUID NOT NULL REFERENCES etl.ingestion_runs(run_id) ON DELETE CASCADE,
    source_file         TEXT NOT NULL,
    target_table        TEXT NOT NULL,
    rows_extracted      BIGINT NOT NULL DEFAULT 0,
    rows_transformed    BIGINT NOT NULL DEFAULT 0,
    rows_loaded         BIGINT NOT NULL DEFAULT 0,
    rows_failed         BIGINT NOT NULL DEFAULT 0,
    duplicate_rows      BIGINT NOT NULL DEFAULT 0,
    null_profile_json   JSONB,
    file_size_bytes     BIGINT,
    file_mtime          TIMESTAMPTZ,
    file_sha256         TEXT,
    duration_seconds    DOUBLE PRECISION,
    reconciled          BOOLEAN GENERATED ALWAYS AS (rows_extracted = rows_loaded) STORED,
    PRIMARY KEY (run_id, source_file)
);

CREATE TABLE IF NOT EXISTS raw.customers (
    customer_id                 TEXT NOT NULL,
    customer_unique_id          TEXT,
    customer_zip_code_prefix    TEXT,
    customer_city               TEXT,
    customer_state              TEXT,
    _source_file                TEXT NOT NULL,
    _row_number                 BIGINT,
    _is_duplicate               BOOLEAN NOT NULL DEFAULT FALSE,
    _quality_flags              JSONB NOT NULL DEFAULT '[]'::jsonb,
    _ingested_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _run_id                     UUID NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.geolocation (
    geolocation_zip_code_prefix TEXT,
    geolocation_lat             DOUBLE PRECISION,
    geolocation_lng             DOUBLE PRECISION,
    geolocation_city            TEXT,
    geolocation_state           TEXT,
    _source_file                TEXT NOT NULL,
    _row_number                 BIGINT,
    _is_duplicate               BOOLEAN NOT NULL DEFAULT FALSE,
    _quality_flags              JSONB NOT NULL DEFAULT '[]'::jsonb,
    _ingested_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _run_id                     UUID NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.order_items (
    order_id                    TEXT NOT NULL,
    order_item_id               INTEGER,
    product_id                  TEXT,
    seller_id                   TEXT,
    shipping_limit_date         TIMESTAMP,
    price                       NUMERIC(12, 2),
    freight_value               NUMERIC(12, 2),
    _source_file                TEXT NOT NULL,
    _row_number                 BIGINT,
    _is_duplicate               BOOLEAN NOT NULL DEFAULT FALSE,
    _quality_flags              JSONB NOT NULL DEFAULT '[]'::jsonb,
    _ingested_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _run_id                     UUID NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.order_payments (
    order_id                    TEXT NOT NULL,
    payment_sequential          INTEGER,
    payment_type                TEXT,
    payment_installments        INTEGER,
    payment_value               NUMERIC(12, 2),
    _source_file                TEXT NOT NULL,
    _row_number                 BIGINT,
    _is_duplicate               BOOLEAN NOT NULL DEFAULT FALSE,
    _quality_flags              JSONB NOT NULL DEFAULT '[]'::jsonb,
    _ingested_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _run_id                     UUID NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.order_reviews (
    review_id                   TEXT,
    order_id                    TEXT,
    review_score                INTEGER,
    review_comment_title        TEXT,
    review_comment_message      TEXT,
    review_creation_date        TIMESTAMP,
    review_answer_timestamp     TIMESTAMP,
    _source_file                TEXT NOT NULL,
    _row_number                 BIGINT,
    _is_duplicate               BOOLEAN NOT NULL DEFAULT FALSE,
    _quality_flags              JSONB NOT NULL DEFAULT '[]'::jsonb,
    _ingested_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _run_id                     UUID NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.orders (
    order_id                        TEXT NOT NULL,
    customer_id                     TEXT,
    order_status                    TEXT,
    order_purchase_timestamp        TIMESTAMP,
    order_approved_at               TIMESTAMP,
    order_delivered_carrier_date    TIMESTAMP,
    order_delivered_customer_date   TIMESTAMP,
    order_estimated_delivery_date   TIMESTAMP,
    _source_file                    TEXT NOT NULL,
    _row_number                     BIGINT,
    _is_duplicate                   BOOLEAN NOT NULL DEFAULT FALSE,
    _quality_flags                  JSONB NOT NULL DEFAULT '[]'::jsonb,
    _ingested_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _run_id                         UUID NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.products (
    product_id                      TEXT NOT NULL,
    product_category_name           TEXT,
    product_name_length             INTEGER,          -- source: product_name_lenght
    product_description_length      INTEGER,          -- source: product_description_lenght
    product_photos_qty              INTEGER,
    product_weight_g                DOUBLE PRECISION,
    product_length_cm               DOUBLE PRECISION,
    product_height_cm               DOUBLE PRECISION,
    product_width_cm                DOUBLE PRECISION,
    _source_file                    TEXT NOT NULL,
    _row_number                     BIGINT,
    _is_duplicate                   BOOLEAN NOT NULL DEFAULT FALSE,
    _quality_flags                  JSONB NOT NULL DEFAULT '[]'::jsonb,
    _ingested_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _run_id                         UUID NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.sellers (
    seller_id                       TEXT NOT NULL,
    seller_zip_code_prefix          TEXT,
    seller_city                     TEXT,
    seller_state                    TEXT,
    _source_file                    TEXT NOT NULL,
    _row_number                     BIGINT,
    _is_duplicate                   BOOLEAN NOT NULL DEFAULT FALSE,
    _quality_flags                  JSONB NOT NULL DEFAULT '[]'::jsonb,
    _ingested_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _run_id                         UUID NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.product_category_translation (
    product_category_name           TEXT NOT NULL,
    product_category_name_english   TEXT,
    _source_file                    TEXT NOT NULL,
    _row_number                     BIGINT,
    _is_duplicate                   BOOLEAN NOT NULL DEFAULT FALSE,
    _quality_flags                  JSONB NOT NULL DEFAULT '[]'::jsonb,
    _ingested_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _run_id                         UUID NOT NULL
);

-- Failed / quarantine rows (never silently discarded)
CREATE TABLE IF NOT EXISTS raw.ingestion_failures (
    failure_id          BIGSERIAL PRIMARY KEY,
    run_id              UUID NOT NULL,
    source_file         TEXT NOT NULL,
    target_table        TEXT,
    row_number          BIGINT,
    error_type          TEXT NOT NULL,
    error_message       TEXT,
    raw_payload         JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
