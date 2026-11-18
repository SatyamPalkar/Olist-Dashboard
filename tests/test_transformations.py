"""ETL / transformation correctness — unit oracle + optional integration hooks."""

from __future__ import annotations

import importlib.util

import pandas as pd
import pytest

from tests.helpers.metrics import detect_join_inflation
from tests.helpers.transforms_reference import (
    transform_geolocation,
    transform_order_items,
    transform_orders,
    transform_payments,
    transform_reviews,
)

pytestmark = [pytest.mark.unit]


def test_transform_orders_types_and_flags(sample_orders: pd.DataFrame) -> None:
    out = transform_orders(sample_orders)
    assert len(out) == 3
    assert out["order_status"].tolist() == ["delivered", "delivered", "canceled"]
    assert out["is_delivered"].tolist() == [True, True, False]
    assert out["is_canceled"].tolist() == [False, False, True]
    # ord_a on-time, ord_b late, ord_c null (no delivery date)
    late = out.set_index("order_id")["is_late_delivery"]
    assert bool(late.loc["ord_a"]) is False
    assert bool(late.loc["ord_b"]) is True
    assert pd.isna(late.loc["ord_c"])


def test_transform_orders_drops_only_invalid_required_fields(
    sample_orders: pd.DataFrame,
) -> None:
    bad = sample_orders.copy()
    bad.loc[len(bad)] = {
        "order_id": "",
        "customer_id": "x",
        "order_status": "created",
        "order_purchase_timestamp": "2018-01-01",
        "order_approved_at": None,
        "order_delivered_carrier_date": None,
        "order_delivered_customer_date": None,
        "order_estimated_delivery_date": None,
    }
    out = transform_orders(bad)
    # Empty order_id discarded; others retained — never silent bulk drop
    assert len(out) == 3
    assert set(out["order_id"]) == {"ord_a", "ord_b", "ord_c"}


def test_transform_order_items_item_total(sample_items: pd.DataFrame) -> None:
    out = transform_order_items(sample_items)
    assert len(out) == 3
    row = out.set_index(["order_id", "order_item_id"]).loc[("ord_a", 1)]
    assert float(row["item_total"]) == pytest.approx(110.0)


def test_transform_payments_keeps_multi_sequential(sample_payments: pd.DataFrame) -> None:
    out = transform_payments(sample_payments)
    assert len(out) == 3
    assert out.groupby("order_id").size().loc["ord_a"] == 2


def test_transform_reviews_retains_duplicate_review_ids(
    sample_reviews: pd.DataFrame,
) -> None:
    out = transform_reviews(sample_reviews)
    assert len(out) == 4
    assert int((out["review_id"] == "rev_dup").sum()) == 2
    assert out["review_score"].between(1, 5).all()


def test_transform_reviews_has_comment_flag(sample_reviews: pd.DataFrame) -> None:
    out = transform_reviews(sample_reviews)
    by_id = out.set_index("review_id")
    # rev_1 has title+message; second ord_a review has message only
    assert bool(by_id.loc["rev_1"]["has_comment"]) is True


def test_transform_geolocation_aggregates_to_one_row_per_zip(
    geolocation_df: pd.DataFrame,
) -> None:
    # Use a sample of prefixes for speed
    sample = geolocation_df.head(5000)
    out = transform_geolocation(sample)
    assert out["zip_code_prefix"].is_unique
    assert (out["point_count"] >= 1).all()


def test_repeated_transform_is_idempotent(sample_orders: pd.DataFrame) -> None:
    once = transform_orders(sample_orders)
    again = transform_orders(sample_orders)
    assert len(once) == len(again) == 3
    assert set(once["order_id"]) == set(again["order_id"])
    # Re-apply on original columns extracted from output
    replay = transform_orders(once[sample_orders.columns])
    assert len(replay) == len(once)
    assert set(replay["order_id"]) == set(once["order_id"])


def test_missing_value_handling_does_not_fill_fake_defaults(
    sample_orders: pd.DataFrame,
) -> None:
    out = transform_orders(sample_orders)
    canceled = out.loc[out["order_id"] == "ord_c"].iloc[0]
    assert pd.isna(canceled["order_delivered_customer_date"])
    assert pd.isna(canceled["delivery_days"])


def test_duplicate_handling_on_order_grain(sample_orders: pd.DataFrame) -> None:
    duped = pd.concat([sample_orders, sample_orders.iloc[[0]]], ignore_index=True)
    out = transform_orders(duped)
    assert out["order_id"].is_unique
    assert len(out) == 3


def test_naive_join_after_transform_still_inflates(
    sample_items: pd.DataFrame, sample_payments: pd.DataFrame
) -> None:
    """Documents why facts must pre-aggregate — transform alone does not fix fan-out."""
    items = transform_order_items(sample_items)
    pays = transform_payments(sample_payments)
    probe = detect_join_inflation(
        items.assign(_m=items["price"]), pays, on="order_id", measure_col="_m"
    )
    assert probe["inflated"] is True
    assert probe["base_sum"] == pytest.approx(350.0)
    # ord_a has 2 payments → its 150 merchandise counted twice → +150 inflation
    assert probe["inflation"] == pytest.approx(150.0)


def test_etl_package_hook_when_present() -> None:
    """If Data Engineer ships etl.load / etl.transform, smoke-import it."""
    for mod_name in ("etl", "etl.load_staging", "etl.transform", "etl.pipeline"):
        spec = importlib.util.find_spec(mod_name)
        if spec is not None:
            module = importlib.import_module(mod_name)
            assert module is not None
            return
    pytest.skip("ETL Python package not implemented yet (Phase 4)")


@pytest.mark.integration
def test_staging_row_counts_vs_raw_when_loaded(orders_df: pd.DataFrame) -> None:
    from tests.helpers import db as db_helper

    if not db_helper.table_exists("staging", "stg_orders"):
        pytest.skip("staging.stg_orders missing")
    stg_count = int(db_helper.scalar("SELECT COUNT(*) FROM staging.stg_orders"))
    # Staging may drop only invalid required keys; expect near-parity
    assert stg_count <= len(orders_df)
    assert stg_count >= int(len(orders_df) * 0.99)
