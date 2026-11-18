"""Source and warehouse contracts derived from docs/dataset_inventory.md
and database/schemas/*.sql.

Do not invent Olist fields. Schema names follow the SQL Architect
implementation (raw / staging / analytics). Orchestrator ADR-003 still
lists dw — see docs/known_data_limitations.md.
"""

from __future__ import annotations

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = Path(
    __import__("os").environ.get("OLIST_RAW_DIR", str(PROJECT_ROOT / "data" / "raw"))
)
CONFIG_PATH = PROJECT_ROOT / "config" / "defaults.yaml"

# Exact Olist filenames (immutable raw contract)
RAW_FILES: dict[str, str] = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

EXPECTED_COLUMNS: dict[str, list[str]] = {
    "customers": [
        "customer_id",
        "customer_unique_id",
        "customer_zip_code_prefix",
        "customer_city",
        "customer_state",
    ],
    "geolocation": [
        "geolocation_zip_code_prefix",
        "geolocation_lat",
        "geolocation_lng",
        "geolocation_city",
        "geolocation_state",
    ],
    "order_items": [
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "shipping_limit_date",
        "price",
        "freight_value",
    ],
    "order_payments": [
        "order_id",
        "payment_sequential",
        "payment_type",
        "payment_installments",
        "payment_value",
    ],
    "order_reviews": [
        "review_id",
        "order_id",
        "review_score",
        "review_comment_title",
        "review_comment_message",
        "review_creation_date",
        "review_answer_timestamp",
    ],
    "orders": [
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "products": [
        "product_id",
        "product_category_name",
        "product_name_lenght",  # source spelling retained
        "product_description_lenght",  # source spelling retained
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ],
    "sellers": [
        "seller_id",
        "seller_zip_code_prefix",
        "seller_city",
        "seller_state",
    ],
    "category_translation": [
        "product_category_name",
        "product_category_name_english",
    ],
}

# Declared primary / natural keys (dataset inventory)
PRIMARY_KEYS: dict[str, list[str]] = {
    "customers": ["customer_id"],
    "orders": ["order_id"],
    "order_items": ["order_id", "order_item_id"],
    "order_payments": ["order_id", "payment_sequential"],
    "order_reviews": ["review_id"],  # NOT reliably unique — known limitation
    "products": ["product_id"],
    "sellers": ["seller_id"],
    "category_translation": ["product_category_name"],
    # geolocation: no unique key at zip grain
}

EXPECTED_ORDER_STATUSES = {
    "delivered",
    "shipped",
    "canceled",
    "unavailable",
    "invoiced",
    "processing",
    "created",
    "approved",
}

EXPECTED_PAYMENT_TYPES = {
    "credit_card",
    "boleto",
    "voucher",
    "debit_card",
    "not_defined",
}

# Warehouse schemas as implemented by SQL Architect
WAREHOUSE_SCHEMAS = ("raw", "staging", "analytics")

STAGING_TABLES = (
    "stg_orders",
    "stg_order_items",
    "stg_order_payments",
    "stg_order_reviews",
    "stg_customers",
    "stg_products",
    "stg_sellers",
    "stg_geolocation",
    "stg_product_category_translation",
)

ANALYTICS_DIMS = (
    "dim_date",
    "dim_geography",
    "dim_customers",
    "dim_products",
    "dim_sellers",
)

ANALYTICS_FACTS = (
    "fact_orders",
    "fact_order_items",
    "fact_payments",
    "fact_order_reviews",
)

# Documented monetary tolerance (BRL) for float/round-trip comparisons
MONEY_TOLERANCE = 0.01


def load_raw_file_list() -> list[str]:
    """Return raw filenames from config/defaults.yaml (fallback to RAW_FILES)."""
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open(encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
        files = cfg.get("raw_files")
        if files:
            return list(files)
    return list(RAW_FILES.values())
