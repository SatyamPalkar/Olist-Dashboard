-- Orchestrate analytics mart loads (dependency order).
\echo '=== Seed: Brazilian states ==='
\i database/seeds/seed_brazilian_states.sql
\echo '=== Seed: dim_date ==='
\i database/seeds/seed_dim_date.sql
\echo '=== Mart: dim_geography ==='
\i database/marts/dim_geography.sql
\echo '=== Mart: dim_customers ==='
\i database/marts/dim_customers.sql
\echo '=== Mart: dim_products ==='
\i database/marts/dim_products.sql
\echo '=== Mart: dim_sellers ==='
\i database/marts/dim_sellers.sql
\echo '=== Mart: fact_orders ==='
\i database/marts/fact_orders.sql
\echo '=== Mart: fact_order_items ==='
\i database/marts/fact_order_items.sql
\echo '=== Mart: fact_payments ==='
\i database/marts/fact_payments.sql
\echo '=== Mart: fact_order_reviews ==='
\i database/marts/fact_order_reviews.sql
\echo '=== Marts complete ==='
