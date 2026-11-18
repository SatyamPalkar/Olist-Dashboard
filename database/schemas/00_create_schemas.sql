-- =============================================================================
-- Create warehouse schemas
-- Safe to re-run.
-- =============================================================================
BEGIN;

CREATE SCHEMA IF NOT EXISTS raw;
COMMENT ON SCHEMA raw IS 'Landing zone: original ingested source data (Olist CSVs). Owned by Data Engineer.';

CREATE SCHEMA IF NOT EXISTS staging;
COMMENT ON SCHEMA staging IS 'Cleaned and standardised business entities. Owned by SQL Architect.';

CREATE SCHEMA IF NOT EXISTS analytics;
COMMENT ON SCHEMA analytics IS 'Star-schema facts, dimensions, and reporting views for Power BI.';

COMMIT;
