-- Refresh staging → marts → materialised views (raw already loaded).
-- Usage: psql -d olist_dw -v ON_ERROR_STOP=1 -f database/scripts/01_refresh_analytics.sql

\echo '=== Staging ==='
\i database/staging/run_staging.sql

\echo '=== Marts ==='
\i database/marts/run_marts.sql

\echo '=== Refresh MVs ==='
REFRESH MATERIALIZED VIEW analytics.mv_monthly_sales;
REFRESH MATERIALIZED VIEW analytics.mv_category_monthly_sales;

\echo '=== REFRESH COMPLETE ==='
