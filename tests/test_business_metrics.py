"""Business metric validation — Python oracle (+ SQL when warehouse loaded).

Metric definitions follow docs/requirements.md and analytics.fact_* comments.
Do not alter definitions here without BA / SQL Architect sign-off.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from tests.helpers import db as db_helper
from tests.helpers.metrics import compute_business_metrics
from tests.helpers.transforms_reference import transform_orders, transform_reviews

pytestmark = [pytest.mark.unit]

_BASELINES = json.loads(
    (Path(__file__).parent / "fixtures" / "baselines.json").read_text(encoding="utf-8")
)


@pytest.fixture(scope="module")
def baselines() -> dict:
    return dict(_BASELINES)


@pytest.fixture(scope="module")
def metrics(orders_df, items_df, payments_df, reviews_df, customers_df):
    return compute_business_metrics(
        orders_df, items_df, payments_df, reviews_df, customers_df
    )


def test_total_orders(metrics, baselines) -> None:
    assert metrics.total_orders == baselines["total_orders"]


def test_merchandise_revenue(metrics, baselines) -> None:
    assert metrics.merchandise_revenue == pytest.approx(
        baselines["merchandise_revenue"], abs=0.05
    )


def test_freight_totals(metrics, baselines) -> None:
    assert metrics.freight_total == pytest.approx(baselines["freight_total"], abs=0.05)


def test_payment_totals(metrics, baselines) -> None:
    assert metrics.payment_total == pytest.approx(baselines["payment_total"], abs=0.05)


def test_average_order_value(metrics) -> None:
    expected = metrics.order_value / metrics.total_orders
    assert metrics.average_order_value == pytest.approx(expected, abs=1e-4)


def test_delivery_metrics(metrics, baselines) -> None:
    assert metrics.delivered_orders == baselines["delivered_orders"]
    assert metrics.late_deliveries == baselines["late_deliveries_with_both_dates"]
    assert metrics.on_time_deliveries + metrics.late_deliveries > 90_000
    assert 0.0 < metrics.on_time_rate < 1.0
    assert metrics.avg_delivery_days > 0


def test_review_score_all_rows_vs_one_per_order(metrics, reviews_df) -> None:
    assert 1.0 <= metrics.avg_review_score_all_reviews <= 5.0
    assert 1.0 <= metrics.avg_review_score_one_per_order <= 5.0
    # Multiplicity means the two averages can differ — both are valid grains
    multi = int((reviews_df.groupby("order_id").size() > 1).sum())
    assert multi > 0


def test_review_one_per_order_matches_transform_rule(
    sample_orders, sample_reviews
) -> None:
    """Latest review_creation_date wins (analytics.fact_orders review_pick)."""
    reviews = transform_reviews(sample_reviews)
    reviews = reviews.sort_values(
        ["order_id", "review_creation_date"], ascending=[True, False]
    )
    one = reviews.drop_duplicates("order_id", keep="first").set_index("order_id")
    assert int(one.loc["ord_a"]["review_score"]) == 4  # later review
    assert int(one.loc["ord_b"]["review_score"]) == 2  # later of duplicate review_id


def test_late_delivery_flag_on_fixture(sample_orders) -> None:
    out = transform_orders(sample_orders).set_index("order_id")
    assert bool(out.loc["ord_b"]["is_late_delivery"]) is True
    assert bool(out.loc["ord_a"]["is_late_delivery"]) is False


def test_repeat_customer_rate(metrics, baselines) -> None:
    assert metrics.unique_customers == baselines["unique_customers"]
    assert metrics.repeat_customers == baselines["repeat_customers"]
    assert metrics.repeat_customer_rate == pytest.approx(
        metrics.repeat_customers / metrics.unique_customers, abs=1e-6
    )


def test_fixture_aov_and_revenue_no_double_count(
    sample_orders, sample_items, sample_payments, sample_reviews
) -> None:
    customers = pd.DataFrame(
        {
            "customer_id": ["cust_1", "cust_2", "cust_3"],
            "customer_unique_id": ["u1", "u2", "u3"],
            "customer_zip_code_prefix": ["1", "2", "3"],
            "customer_city": ["a", "b", "c"],
            "customer_state": ["SP", "RJ", "MG"],
        }
    )
    m = compute_business_metrics(
        sample_orders, sample_items, sample_payments, sample_reviews, customers
    )
    # merchandise = 100+50+200 = 350; freight = 10+5+20 = 35
    assert m.merchandise_revenue == pytest.approx(350.0)
    assert m.freight_total == pytest.approx(35.0)
    assert m.payment_total == pytest.approx(385.0)
    assert m.total_orders == 3


@pytest.mark.integration
@pytest.mark.requires_warehouse
def test_sql_avg_review_vs_python(metrics) -> None:
    sql_avg = float(
        db_helper.scalar(
            "SELECT AVG(review_score)::float FROM analytics.fact_order_reviews"
        )
    )
    assert sql_avg == pytest.approx(metrics.avg_review_score_all_reviews, abs=0.02)


@pytest.mark.integration
@pytest.mark.requires_warehouse
def test_sql_on_time_rate_vs_python(metrics) -> None:
    row = db_helper.read_sql(
        """
        SELECT
            COUNT(*) FILTER (
                WHERE is_delivered
                  AND is_late_delivery IS FALSE
                  AND delivered_customer_date_key IS NOT NULL
                  AND estimated_delivery_date_key IS NOT NULL
            ) AS on_time,
            COUNT(*) FILTER (
                WHERE is_delivered
                  AND is_late_delivery IS TRUE
            ) AS late
        FROM analytics.fact_orders
        """
    ).iloc[0]
    denom = int(row["on_time"]) + int(row["late"])
    if denom == 0:
        pytest.skip("No delivery flags populated yet")
    sql_rate = int(row["on_time"]) / denom
    assert sql_rate == pytest.approx(metrics.on_time_rate, abs=0.02)
