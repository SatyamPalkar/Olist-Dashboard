"""Configuration for the Olist ETL pipeline (env-driven, no hardcoded secrets)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# Project root: parent of the etl/ package
PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class DatasetConfig:
    """Mapping of a source CSV to a raw PostgreSQL table."""

    source_file: str
    target_table: str
    primary_keys: tuple[str, ...]
    date_columns: tuple[str, ...] = ()
    int_columns: tuple[str, ...] = ()
    float_columns: tuple[str, ...] = ()
    numeric_columns: tuple[str, ...] = ()
    text_columns: tuple[str, ...] = ()
    column_renames: dict[str, str] = field(default_factory=dict)
    chunk_size: int | None = None
    required_columns: tuple[str, ...] = ()


# Source → raw table contracts (aligned with sql/01_raw_schema.sql)
DATASETS: dict[str, DatasetConfig] = {
    "customers": DatasetConfig(
        source_file="olist_customers_dataset.csv",
        target_table="customers",
        primary_keys=("customer_id",),
        text_columns=(
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ),
        required_columns=("customer_id",),
    ),
    "geolocation": DatasetConfig(
        source_file="olist_geolocation_dataset.csv",
        target_table="geolocation",
        primary_keys=(),  # no natural unique key; many duplicate rows in source
        float_columns=("geolocation_lat", "geolocation_lng"),
        text_columns=(
            "geolocation_zip_code_prefix",
            "geolocation_city",
            "geolocation_state",
        ),
        chunk_size=100_000,
    ),
    "order_items": DatasetConfig(
        source_file="olist_order_items_dataset.csv",
        target_table="order_items",
        primary_keys=("order_id", "order_item_id"),
        date_columns=("shipping_limit_date",),
        int_columns=("order_item_id",),
        numeric_columns=("price", "freight_value"),
        text_columns=("order_id", "product_id", "seller_id"),
        required_columns=("order_id", "order_item_id"),
    ),
    "order_payments": DatasetConfig(
        source_file="olist_order_payments_dataset.csv",
        target_table="order_payments",
        primary_keys=("order_id", "payment_sequential"),
        int_columns=("payment_sequential", "payment_installments"),
        numeric_columns=("payment_value",),
        text_columns=("order_id", "payment_type"),
        required_columns=("order_id", "payment_sequential"),
    ),
    "order_reviews": DatasetConfig(
        source_file="olist_order_reviews_dataset.csv",
        target_table="order_reviews",
        primary_keys=(),  # review_id is NOT unique in source (~814 duplicate ids)
        date_columns=("review_creation_date", "review_answer_timestamp"),
        int_columns=("review_score",),
        text_columns=(
            "review_id",
            "order_id",
            "review_comment_title",
            "review_comment_message",
        ),
        required_columns=("review_id", "order_id"),
    ),
    "orders": DatasetConfig(
        source_file="olist_orders_dataset.csv",
        target_table="orders",
        primary_keys=("order_id",),
        date_columns=(
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ),
        text_columns=("order_id", "customer_id", "order_status"),
        required_columns=("order_id", "customer_id"),
    ),
    "products": DatasetConfig(
        source_file="olist_products_dataset.csv",
        target_table="products",
        primary_keys=("product_id",),
        int_columns=(
            "product_name_length",
            "product_description_length",
            "product_photos_qty",
        ),
        float_columns=(
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ),
        text_columns=("product_id", "product_category_name"),
        column_renames={
            "product_name_lenght": "product_name_length",
            "product_description_lenght": "product_description_length",
        },
        required_columns=("product_id",),
    ),
    "sellers": DatasetConfig(
        source_file="olist_sellers_dataset.csv",
        target_table="sellers",
        primary_keys=("seller_id",),
        text_columns=(
            "seller_id",
            "seller_zip_code_prefix",
            "seller_city",
            "seller_state",
        ),
        required_columns=("seller_id",),
    ),
    "product_category_translation": DatasetConfig(
        source_file="product_category_name_translation.csv",
        target_table="product_category_translation",
        primary_keys=("product_category_name",),
        text_columns=("product_category_name", "product_category_name_english"),
        required_columns=("product_category_name",),
    ),
}


@dataclass
class Settings:
    """Runtime settings loaded from environment variables."""

    data_dir: Path = field(default_factory=lambda: Path(os.getenv("OLIST_DATA_DIR", str(PROJECT_ROOT / "data" / "raw"))))
    schema_sql: Path = field(default_factory=lambda: PROJECT_ROOT / "sql" / "01_raw_schema.sql")
    log_dir: Path = field(default_factory=lambda: Path(os.getenv("OLIST_LOG_DIR", str(PROJECT_ROOT / "logs"))))
    raw_schema: str = field(default_factory=lambda: os.getenv("OLIST_RAW_SCHEMA", "raw"))
    etl_schema: str = field(default_factory=lambda: os.getenv("OLIST_ETL_SCHEMA", "etl"))
    batch_size: int = field(default_factory=lambda: int(os.getenv("OLIST_BATCH_SIZE", "5000")))
    db_host: str = field(default_factory=lambda: os.getenv("POSTGRES_HOST", "localhost"))
    db_port: int = field(default_factory=lambda: int(os.getenv("POSTGRES_PORT", "5432")))
    db_name: str = field(default_factory=lambda: os.getenv("POSTGRES_DB", "retail_bi"))
    db_user: str = field(default_factory=lambda: os.getenv("POSTGRES_USER", "retail_bi"))
    db_password: str = field(default_factory=lambda: os.getenv("POSTGRES_PASSWORD", "retail_bi"))
    db_pool_size: int = field(default_factory=lambda: int(os.getenv("POSTGRES_POOL_SIZE", "5")))
    csv_encoding: str = field(default_factory=lambda: os.getenv("OLIST_CSV_ENCODING", "utf-8"))
    datasets: dict[str, DatasetConfig] = field(default_factory=lambda: dict(DATASETS))

    @property
    def database_url(self) -> str:
        """SQLAlchemy URL using the psycopg (v3) driver."""
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    def as_safe_dict(self) -> dict[str, Any]:
        """Return config suitable for logging (password redacted)."""
        return {
            "data_dir": str(self.data_dir),
            "raw_schema": self.raw_schema,
            "etl_schema": self.etl_schema,
            "batch_size": self.batch_size,
            "db_host": self.db_host,
            "db_port": self.db_port,
            "db_name": self.db_name,
            "db_user": self.db_user,
            "db_password": "***",
            "csv_encoding": self.csv_encoding,
            "dataset_count": len(self.datasets),
        }


def get_settings() -> Settings:
    """Build settings from the current environment."""
    return Settings()
