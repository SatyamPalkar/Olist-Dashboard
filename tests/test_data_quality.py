"""Cross-cutting data quality — nulls, duplicates, orphans, unexpected values,
and double-counting / relationship checks on raw data.
"""

from __future__ import annotations

import pandas as pd
import pytest

from tests.helpers.metrics import detect_join_inflation
from tests.helpers.raw_loader import null_report

pytestmark = [pytest.mark.raw, pytest.mark.unit]


def test_orphan_foreign_keys_orders_spine(
    orders_df: pd.DataFrame,
    items_df: pd.DataFrame,
    payments_df: pd.DataFrame,
    reviews_df: pd.DataFrame,
    customers_df: pd.DataFrame,
) -> None:
    oid = set(orders_df["order_id"])
    assert (~items_df["order_id"].isin(oid)).sum() == 0
    assert (~payments_df["order_id"].isin(oid)).sum() == 0
    assert (~reviews_df["order_id"].isin(oid)).sum() == 0
    assert (~orders_df["customer_id"].isin(customers_df["customer_id"])).sum() == 0


def test_orphan_product_and_seller_keys(
    items_df: pd.DataFrame, products_df: pd.DataFrame, sellers_df: pd.DataFrame
) -> None:
    assert (~items_df["product_id"].isin(products_df["product_id"])).sum() == 0
    assert (~items_df["seller_id"].isin(sellers_df["seller_id"])).sum() == 0


def test_category_translation_coverage_is_quantified(
    products_df: pd.DataFrame, translation_df: pd.DataFrame
) -> None:
    cats = products_df["product_category_name"].dropna()
    missing = int((~cats.isin(translation_df["product_category_name"])).sum())
    # Known limitation: a small number of categories lack English mapping
    assert missing >= 0
    assert missing < 50  # quantified bound — do not silently drop products


def test_null_counts_on_delivery_fields(orders_df: pd.DataFrame) -> None:
    report = null_report(orders_df)
    assert report.get("order_delivered_customer_date", 0) > 0
    # Estimated delivery is populated for all rows in public dump
    assert "order_estimated_delivery_date" not in report


def test_duplicate_identifiers_inventory(
    orders_df: pd.DataFrame,
    reviews_df: pd.DataFrame,
    geolocation_df: pd.DataFrame,
) -> None:
    assert orders_df["order_id"].is_unique
    assert not reviews_df["review_id"].is_unique
    assert not geolocation_df["geolocation_zip_code_prefix"].is_unique


# ---------------------------------------------------------------------------
# Double-counting / relationship checks
# ---------------------------------------------------------------------------


def test_multiple_items_per_order_exist(items_df: pd.DataFrame) -> None:
    multi = int((items_df.groupby("order_id").size() > 1).sum())
    assert multi > 0
    assert items_df.groupby("order_id").size().max() >= 2


def test_multiple_payments_per_order_exist(payments_df: pd.DataFrame) -> None:
    multi = int((payments_df.groupby("order_id").size() > 1).sum())
    assert multi > 0


def test_multiple_reviews_per_order_exist(reviews_df: pd.DataFrame) -> None:
    multi = int((reviews_df.groupby("order_id").size() > 1).sum())
    assert multi > 0


def test_customer_id_is_order_scoped_not_person(
    customers_df: pd.DataFrame, orders_df: pd.DataFrame
) -> None:
    assert customers_df["customer_id"].is_unique
    assert customers_df["customer_unique_id"].nunique() < len(customers_df)
    assert len(customers_df) == len(orders_df)


def test_seller_to_product_is_many_to_many_via_items(
    items_df: pd.DataFrame,
) -> None:
    sellers_per_product = items_df.groupby("product_id")["seller_id"].nunique()
    products_per_seller = items_df.groupby("seller_id")["product_id"].nunique()
    assert (sellers_per_product > 1).any() or (products_per_seller > 1).any()


def test_joining_items_to_payments_inflates_revenue(
    items_df: pd.DataFrame, payments_df: pd.DataFrame
) -> None:
    probe = detect_join_inflation(
        items_df.assign(_m=pd.to_numeric(items_df["price"])),
        payments_df,
        on="order_id",
        measure_col="_m",
    )
    assert probe["inflated"] is True
    assert probe["inflation"] > 0


def test_joining_items_to_reviews_inflates_revenue(
    items_df: pd.DataFrame, reviews_df: pd.DataFrame
) -> None:
    probe = detect_join_inflation(
        items_df.assign(_m=pd.to_numeric(items_df["price"])),
        reviews_df,
        on="order_id",
        measure_col="_m",
    )
    assert probe["inflated"] is True


def test_preaggregate_payments_before_join_avoids_inflation(
    items_df: pd.DataFrame, payments_df: pd.DataFrame
) -> None:
    """Correct pattern used by analytics.fact_orders."""
    merch = float(pd.to_numeric(items_df["price"]).sum())
    pay_agg = (
        payments_df.groupby("order_id", as_index=False)["payment_value"]
        .sum()
        .rename(columns={"payment_value": "payment_amount"})
    )
    item_agg = (
        items_df.assign(price=pd.to_numeric(items_df["price"]))
        .groupby("order_id", as_index=False)["price"]
        .sum()
    )
    merged = item_agg.merge(pay_agg, on="order_id", how="left")
    assert float(merged["price"].sum()) == pytest.approx(merch, abs=0.01)


def test_brazilian_state_codes_look_valid(customers_df: pd.DataFrame) -> None:
    states = set(customers_df["customer_state"].astype(str).str.upper().unique())
    # All should be 2-letter codes
    assert all(len(s) == 2 for s in states)
    assert "SP" in states
