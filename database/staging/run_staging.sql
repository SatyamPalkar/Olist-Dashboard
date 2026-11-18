-- Orchestrate staging transforms (dependency order).
-- Prerequisite: raw.* loaded by Data Engineer.
\echo '=== Staging: category translation ==='
\i database/staging/stg_product_category_translation.sql
\echo '=== Staging: geolocation ==='
\i database/staging/stg_geolocation.sql
\echo '=== Staging: customers ==='
\i database/staging/stg_customers.sql
\echo '=== Staging: sellers ==='
\i database/staging/stg_sellers.sql
\echo '=== Staging: products ==='
\i database/staging/stg_products.sql
\echo '=== Staging: orders ==='
\i database/staging/stg_orders.sql
\echo '=== Staging: order_items ==='
\i database/staging/stg_order_items.sql
\echo '=== Staging: order_payments ==='
\i database/staging/stg_order_payments.sql
\echo '=== Staging: order_reviews ==='
\i database/staging/stg_order_reviews.sql
\echo '=== Staging complete ==='
