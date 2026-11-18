-- =============================================================================
-- Full warehouse build (DDL → staging → marts → views → indexes)
-- Prerequisite: PostgreSQL database created; raw CSVs loaded into raw.* after
--               schemas/01_raw_tables.sql (Data Engineer step).
--
-- Usage (from repo root):
--   psql -d olist_bi -v ON_ERROR_STOP=1 -f database/scripts/00_run_all.sql
--   (database name from .env POSTGRES_DB; default olist_bi)
-- =============================================================================

\echo '=== 1. Schemas ==='
\i database/schemas/00_create_schemas.sql

-- The raw tables and data must already exist. Do not recreate them here.
-- For a complete destructive rebuild, use scripts/build_warehouse.py --rebuild.

\echo '=== 3. Staging DDL ==='
\i database/schemas/02_staging_tables.sql

\echo '=== 4. Analytics DDL ==='
\i database/schemas/03_analytics_tables.sql

\echo '=== 5. Staging transforms ==='
\i database/staging/run_staging.sql

\echo '=== 6. Marts ==='
\i database/marts/run_marts.sql

\echo '=== 7. Indexes ==='
\i database/schemas/04_indexes.sql

\echo '=== 8. Reporting views ==='
\i database/views/vw_reporting_kpis.sql

\echo '=== 9. Materialised views ==='
\i database/views/mv_monthly_sales.sql

\echo '=== BUILD COMPLETE ==='
