"""Pytest fixtures for Data QA — raw CSVs, optional warehouse, sample fixtures."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tests.helpers import db as db_helper
from tests.helpers.contracts import PROJECT_ROOT, RAW_DIR, RAW_FILES
from tests.helpers.raw_loader import load_raw


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "unit: fast tests with no database dependency")
    config.addinivalue_line(
        "markers", "integration: requires PostgreSQL and loaded warehouse"
    )
    config.addinivalue_line(
        "markers", "requires_warehouse: analytics facts/dims must be populated"
    )
    config.addinivalue_line("markers", "raw: validates immutable data/raw CSVs")
    config.addinivalue_line("markers", "slow: longer-running checks over full datasets")


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def raw_dir() -> Path:
    return RAW_DIR


@pytest.fixture(scope="session")
def raw_files() -> dict[str, str]:
    return dict(RAW_FILES)


@pytest.fixture(scope="session")
def orders_df() -> pd.DataFrame:
    return load_raw("orders")


@pytest.fixture(scope="session")
def items_df() -> pd.DataFrame:
    return load_raw("order_items")


@pytest.fixture(scope="session")
def payments_df() -> pd.DataFrame:
    return load_raw("order_payments")


@pytest.fixture(scope="session")
def reviews_df() -> pd.DataFrame:
    return load_raw("order_reviews")


@pytest.fixture(scope="session")
def customers_df() -> pd.DataFrame:
    return load_raw("customers")


@pytest.fixture(scope="session")
def products_df() -> pd.DataFrame:
    return load_raw("products")


@pytest.fixture(scope="session")
def sellers_df() -> pd.DataFrame:
    return load_raw("sellers")


@pytest.fixture(scope="session")
def geolocation_df() -> pd.DataFrame:
    return load_raw("geolocation")


@pytest.fixture(scope="session")
def translation_df() -> pd.DataFrame:
    return load_raw("category_translation")


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_orders(fixtures_dir: Path) -> pd.DataFrame:
    return pd.read_csv(fixtures_dir / "sample_orders.csv")


@pytest.fixture
def sample_items(fixtures_dir: Path) -> pd.DataFrame:
    return pd.read_csv(fixtures_dir / "sample_order_items.csv")


@pytest.fixture
def sample_payments(fixtures_dir: Path) -> pd.DataFrame:
    return pd.read_csv(fixtures_dir / "sample_order_payments.csv")


@pytest.fixture
def sample_reviews(fixtures_dir: Path) -> pd.DataFrame:
    return pd.read_csv(fixtures_dir / "sample_order_reviews.csv")


@pytest.fixture(scope="session")
def db_is_up() -> bool:
    return db_helper.database_available()


@pytest.fixture(scope="session")
def warehouse_ready() -> bool:
    return db_helper.warehouse_loaded()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-skip integration tests when Postgres / warehouse is unavailable."""
    db_up = db_helper.database_available()
    wh_up = db_helper.warehouse_loaded() if db_up else False
    skip_db = pytest.mark.skip(reason="PostgreSQL not available (set POSTGRES_* env)")
    skip_wh = pytest.mark.skip(
        reason="analytics warehouse not loaded (run ETL + marts first)"
    )
    for item in items:
        if "integration" in item.keywords:
            if not db_up:
                item.add_marker(skip_db)
            elif "warehouse" in item.keywords or "requires_warehouse" in item.keywords:
                if not wh_up:
                    item.add_marker(skip_wh)
