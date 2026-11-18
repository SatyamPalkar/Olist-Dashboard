#!/usr/bin/env python3
"""Rebuild the Olist warehouse in a dedicated PostgreSQL database using psql.

This is a destructive full rebuild of the project's raw, staging and analytics
objects. Set standard libpq PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD variables.
"""
from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DATASETS = {
    'olist_orders': ('olist_orders_dataset.csv', 'order_id customer_id order_status order_purchase_timestamp order_approved_at order_delivered_carrier_date order_delivered_customer_date order_estimated_delivery_date'),
    'olist_order_items': ('olist_order_items_dataset.csv', 'order_id order_item_id product_id seller_id shipping_limit_date price freight_value'),
    'olist_order_payments': ('olist_order_payments_dataset.csv', 'order_id payment_sequential payment_type payment_installments payment_value'),
    'olist_order_reviews': ('olist_order_reviews_dataset.csv', 'review_id order_id review_score review_comment_title review_comment_message review_creation_date review_answer_timestamp'),
    'olist_customers': ('olist_customers_dataset.csv', 'customer_id customer_unique_id customer_zip_code_prefix customer_city customer_state'),
    'olist_products': ('olist_products_dataset.csv', 'product_id product_category_name product_name_lenght product_description_lenght product_photos_qty product_weight_g product_length_cm product_height_cm product_width_cm'),
    'olist_sellers': ('olist_sellers_dataset.csv', 'seller_id seller_zip_code_prefix seller_city seller_state'),
    'olist_geolocation': ('olist_geolocation_dataset.csv', 'geolocation_zip_code_prefix geolocation_lat geolocation_lng geolocation_city geolocation_state'),
    'product_category_name_translation': ('product_category_name_translation.csv', 'product_category_name product_category_name_english'),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'data/raw')
    parser.add_argument('--rebuild', action='store_true', help='Required: replace project warehouse tables and data')
    args = parser.parse_args()
    if not args.rebuild:
        parser.error('pass --rebuild to acknowledge that project warehouse tables are replaced')
    if not os.environ.get('PGDATABASE'):
        parser.error('set PGDATABASE to the dedicated target database')
    counts = {}
    paths = {}
    for table, (filename, columns) in DATASETS.items():
        path = (args.data_dir / filename).resolve()
        if any(c in str(path) for c in "'\n\r\\"):
            raise ValueError(f'Unsupported character in CSV path: {path}')
        with path.open(encoding='utf-8-sig', newline='') as source:
            reader = csv.reader(source)
            header = next(reader)
            if header != columns.split():
                raise ValueError(f'Unexpected columns in {filename}: {header}')
            counts[table] = sum(1 for _ in reader)
        paths[table] = path
        print(f'Validated {filename}: {counts[table]:,} rows', flush=True)
    lines = ['\\set ON_ERROR_STOP on', r'\i database/schemas/00_create_schemas.sql',
             r'\i database/schemas/01_raw_tables.sql', r'\i database/schemas/02_staging_tables.sql',
             r'\i database/schemas/03_analytics_tables.sql', 'BEGIN;']
    for table, (_, columns) in DATASETS.items():
        lines.append(f"\\copy raw.{table} ({', '.join(columns.split())}) FROM '{paths[table]}' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')")
        lines.append(f"DO $$ BEGIN IF (SELECT count(*) FROM raw.{table}) <> {counts[table]} THEN RAISE EXCEPTION 'Row count mismatch: {table}'; END IF; END $$;")
    lines += ['COMMIT;', r'\i database/staging/run_staging.sql', r'\i database/marts/run_marts.sql',
              r'\i database/schemas/04_indexes.sql', r'\i database/views/vw_reporting_kpis.sql',
              r'\i database/views/mv_monthly_sales.sql', r"SELECT 'fact_orders' AS table_name, count(*) AS rows FROM analytics.fact_orders;"]
    with tempfile.NamedTemporaryFile('w', suffix='.sql', encoding='utf-8') as script:
        script.write('\n'.join(lines) + '\n')
        script.flush()
        return subprocess.run(['psql', '-X', '-v', 'ON_ERROR_STOP=1', '-f', script.name], cwd=ROOT, check=False).returncode


if __name__ == '__main__':
    sys.exit(main())
