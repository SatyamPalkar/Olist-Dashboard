"""Reconciliation — Python oracle vs SQL warehouse; payment vs merchandise gaps."""

from __future__ import annotations

import pytest

from tests.helpers.contracts import MONEY_TOLERANCE
from tests.helpers import db as db_helper
from tests.helpers.metrics import compute_business_metrics

pytestmark = [pytest.mark.unit]


def test_payment_vs_order_value_gap_is_quantified(
    orders_df,
    items_df,
    payments_df,
    reviews_df,
    customers_df,
) -> None:
    m = compute_business_metrics(
        orders_df, items_df, payments_df, reviews_df, customers_df
    )
    # Documented source discrepancy (vouchers / order gaps) — quantify, don't "fix"
    assert abs(m.payment_minus_order_value) > MONEY_TOLERANCE
    # Bound the gap so regressions are caught if data changes drastically
    assert abs(m.payment_minus_order_value) < 500_000


def test_orders_without_items_quantified(
    orders_df, items_df, payments_df, reviews_df, customers_df
) -> None:
    m = compute_business_metrics(
        orders_df, items_df, payments_df, reviews_df, customers_df
    )
    assert m.orders_without_items > 0
    assert m.orders_without_items < 5_000


def test_orders_without_payments_rare(
    orders_df, items_df, payments_df, reviews_df, customers_df
) -> None:
    m = compute_business_metrics(
        orders_df, items_df, payments_df, reviews_df, customers_df
    )
    assert m.orders_without_payments <= 5


def test_python_metric_totals_are_internally_consistent(
    orders_df, items_df, payments_df, reviews_df, customers_df
) -> None:
    m = compute_business_metrics(
        orders_df, items_df, payments_df, reviews_df, customers_df
    )
    assert m.order_value == pytest.approx(
        m.merchandise_revenue + m.freight_total, abs=MONEY_TOLERANCE
    )
    assert m.average_order_value == pytest.approx(
        m.order_value / m.total_orders, abs=0.0001
    )
    assert m.on_time_deliveries + m.late_deliveries > 0
    assert m.on_time_rate + m.late_rate == pytest.approx(1.0, abs=1e-6)


@pytest.mark.integration
@pytest.mark.requires_warehouse
def test_reconcile_order_count_sql_vs_python(orders_df) -> None:
    sql_count = int(db_helper.scalar("SELECT COUNT(*) FROM analytics.fact_orders"))
    # fact_orders may exclude rows failing date-dim join; allow small documented delta
    delta = abs(sql_count - len(orders_df))
    assert delta < 100, f"order count delta {delta} (sql={sql_count}, raw={len(orders_df)})"


@pytest.mark.integration
@pytest.mark.requires_warehouse
def test_reconcile_merchandise_sql_vs_python(items_df) -> None:
    py = float(__import__("pandas").to_numeric(items_df["price"]).sum())
    sql = float(
        db_helper.scalar("SELECT COALESCE(SUM(merchandise_sales),0) FROM analytics.fact_orders")
    )
    sql_items = float(
        db_helper.scalar("SELECT COALESCE(SUM(price),0) FROM analytics.fact_order_items")
    )
    assert sql == pytest.approx(sql_items, abs=0.05)
    # Item fact should match raw merchandise closely
    assert abs(sql_items - py) < 1.0


@pytest.mark.integration
@pytest.mark.requires_warehouse
def test_reconcile_payment_total_sql_vs_python(payments_df) -> None:
    py = float(__import__("pandas").to_numeric(payments_df["payment_value"]).sum())
    sql = float(
        db_helper.scalar("SELECT COALESCE(SUM(payment_value),0) FROM analytics.fact_payments")
    )
    assert abs(sql - py) < 1.0


@pytest.mark.integration
@pytest.mark.requires_warehouse
def test_reconcile_freight_sql_vs_python(items_df) -> None:
    py = float(__import__("pandas").to_numeric(items_df["freight_value"]).sum())
    sql = float(
        db_helper.scalar("SELECT COALESCE(SUM(freight_charges),0) FROM analytics.fact_orders")
    )
    assert abs(sql - py) < 1.0


@pytest.mark.integration
@pytest.mark.requires_warehouse
def test_fact_orders_payment_amount_equals_payment_fact_sum() -> None:
    diff = float(
        db_helper.scalar(
            """
            WITH p AS (
                SELECT order_id, SUM(payment_value) AS pay
                FROM analytics.fact_payments
                GROUP BY order_id
            )
            SELECT COALESCE(SUM(ABS(f.payment_amount - COALESCE(p.pay, 0))), 0)
            FROM analytics.fact_orders f
            LEFT JOIN p ON p.order_id = f.order_id
            """
        )
    )
    assert diff < 0.05
