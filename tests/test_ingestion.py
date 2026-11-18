"""Raw data validation — source availability, columns, types, nulls, keys, dates."""

from __future__ import annotations

import pandas as pd
import pytest

from tests.helpers.contracts import (
    EXPECTED_COLUMNS,
    EXPECTED_ORDER_STATUSES,
    EXPECTED_PAYMENT_TYPES,
    PRIMARY_KEYS,
    RAW_FILES,
)
from tests.helpers.raw_loader import assert_raw_available, load_raw, null_report

pytestmark = [pytest.mark.raw, pytest.mark.unit]


@pytest.mark.parametrize("entity", list(RAW_FILES.keys()))
def test_source_file_available(entity: str) -> None:
    path = assert_raw_available(entity)
    assert path.stat().st_size > 0


@pytest.mark.parametrize("entity", list(EXPECTED_COLUMNS.keys()))
def test_expected_columns_present(entity: str) -> None:
    df = load_raw(entity)
    missing = [c for c in EXPECTED_COLUMNS[entity] if c not in df.columns]
    assert missing == [], f"{entity} missing columns: {missing}"


@pytest.mark.parametrize("entity", list(RAW_FILES.keys()))
def test_non_empty_datasets(entity: str) -> None:
    df = load_raw(entity)
    assert len(df) > 0


def test_orders_row_count_matches_customers(
    orders_df: pd.DataFrame, customers_df: pd.DataFrame
) -> None:
    """Olist: one customer_id per order → equal row counts."""
    assert len(orders_df) == len(customers_df)


@pytest.mark.parametrize(
    "entity,keys",
    [(e, k) for e, k in PRIMARY_KEYS.items() if e != "order_reviews"],
)
def test_declared_primary_keys_unique(entity: str, keys: list[str]) -> None:
    df = load_raw(entity)
    dups = int(df.duplicated(subset=keys).sum())
    assert dups == 0, f"{entity} has {dups} duplicate key rows on {keys}"


def test_review_id_not_reliably_unique_is_documented(reviews_df: pd.DataFrame) -> None:
    """Known source limitation — must NOT be silently 'fixed' by dropping rows."""
    dups = int(reviews_df["review_id"].duplicated().sum())
    assert dups > 0, "Expected known duplicate review_id rows in Olist public dump"
    # All rows retained
    assert len(reviews_df) == dups + reviews_df["review_id"].nunique()


def test_geolocation_zip_not_unique(geolocation_df: pd.DataFrame) -> None:
    assert not geolocation_df["geolocation_zip_code_prefix"].is_unique
    assert geolocation_df["geolocation_zip_code_prefix"].nunique() < len(geolocation_df)


def test_critical_id_columns_have_no_nulls(
    orders_df: pd.DataFrame,
    items_df: pd.DataFrame,
    payments_df: pd.DataFrame,
    customers_df: pd.DataFrame,
) -> None:
    assert orders_df[["order_id", "customer_id", "order_status"]].isna().sum().sum() == 0
    assert items_df[["order_id", "order_item_id", "product_id", "seller_id"]].isna().sum().sum() == 0
    assert payments_df[["order_id", "payment_sequential", "payment_type"]].isna().sum().sum() == 0
    assert customers_df[["customer_id", "customer_unique_id"]].isna().sum().sum() == 0


def test_order_purchase_timestamps_parse(orders_df: pd.DataFrame) -> None:
    parsed = pd.to_datetime(orders_df["order_purchase_timestamp"], errors="coerce")
    assert parsed.isna().sum() == 0
    assert parsed.min() >= pd.Timestamp("2016-01-01")
    assert parsed.max() <= pd.Timestamp("2019-01-01")


def test_invalid_dates_are_null_not_garbage(orders_df: pd.DataFrame) -> None:
    """Nullable timestamps must either parse or be null — no silent garbage strings."""
    for col in (
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ):
        series = orders_df[col]
        non_null = series.dropna()
        parsed = pd.to_datetime(non_null, errors="coerce")
        bad = int(parsed.isna().sum())
        assert bad == 0, f"{col} has {bad} non-null values that do not parse as dates"


def test_order_status_domain(orders_df: pd.DataFrame) -> None:
    unexpected = set(orders_df["order_status"].str.lower().unique()) - EXPECTED_ORDER_STATUSES
    assert unexpected == set(), f"Unexpected order_status values: {unexpected}"


def test_payment_type_domain(payments_df: pd.DataFrame) -> None:
    unexpected = set(payments_df["payment_type"].str.lower().unique()) - EXPECTED_PAYMENT_TYPES
    assert unexpected == set(), f"Unexpected payment_type values: {unexpected}"


def test_review_score_domain(reviews_df: pd.DataFrame) -> None:
    scores = pd.to_numeric(reviews_df["review_score"], errors="coerce")
    assert scores.isna().sum() == 0
    assert scores.between(1, 5).all()


def test_price_and_freight_non_negative(items_df: pd.DataFrame) -> None:
    price = pd.to_numeric(items_df["price"], errors="coerce")
    freight = pd.to_numeric(items_df["freight_value"], errors="coerce")
    assert price.notna().all()
    assert freight.notna().all()
    assert (price >= 0).all()
    assert (freight >= 0).all()


def test_null_inventory_is_reported_not_discarded(orders_df: pd.DataFrame) -> None:
    """Nulls on optional timestamps are expected; rows must remain."""
    report = null_report(orders_df)
    assert "order_approved_at" in report
    assert report["order_approved_at"] > 0
    assert len(orders_df) > 90_000


def test_numeric_type_coercion_for_measures(items_df: pd.DataFrame, payments_df: pd.DataFrame) -> None:
    assert pd.to_numeric(items_df["price"], errors="coerce").notna().all()
    assert pd.to_numeric(payments_df["payment_value"], errors="coerce").notna().all()
    assert pd.to_numeric(payments_df["payment_installments"], errors="coerce").notna().all()
