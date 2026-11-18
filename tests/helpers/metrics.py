"""Independent Python KPI calculations (oracle) for reconciliation.

Definitions follow docs/requirements.md and analytics.fact_* comments.
Do not change these definitions without BA / SQL Architect coordination.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass(frozen=True)
class BusinessMetrics:
    total_orders: int
    merchandise_revenue: float
    freight_total: float
    order_value: float  # merchandise + freight
    payment_total: float
    average_order_value: float
    avg_review_score_all_reviews: float
    avg_review_score_one_per_order: float
    delivered_orders: int
    on_time_deliveries: int
    late_deliveries: int
    on_time_rate: float
    late_rate: float
    avg_delivery_days: float
    unique_customers: int
    repeat_customers: int
    repeat_customer_rate: float
    orders_without_items: int
    orders_without_payments: int
    payment_minus_order_value: float

    def to_dict(self) -> dict:
        return asdict(self)


def _money(series: pd.Series) -> float:
    return float(pd.to_numeric(series, errors="coerce").fillna(0).sum())


def compute_business_metrics(
    orders: pd.DataFrame,
    items: pd.DataFrame,
    payments: pd.DataFrame,
    reviews: pd.DataFrame,
    customers: pd.DataFrame,
) -> BusinessMetrics:
    """Compute KPIs from raw (or staging-equivalent) frames."""
    total_orders = int(orders["order_id"].nunique())
    merchandise = _money(items["price"])
    freight = _money(items["freight_value"])
    order_value = merchandise + freight
    payment_total = _money(payments["payment_value"])
    aov = order_value / total_orders if total_orders else 0.0

    scores = pd.to_numeric(reviews["review_score"], errors="coerce")
    avg_all = float(scores.mean()) if len(scores) else float("nan")

    # One score per order: latest review_creation_date (matches fact_orders CTE)
    rev = reviews.copy()
    rev["review_score"] = pd.to_numeric(rev["review_score"], errors="coerce")
    rev["review_creation_date"] = pd.to_datetime(
        rev["review_creation_date"], errors="coerce"
    )
    rev = rev.sort_values(
        ["order_id", "review_creation_date"], ascending=[True, False]
    )
    one_per_order = rev.drop_duplicates("order_id", keep="first")
    avg_one = float(one_per_order["review_score"].mean()) if len(one_per_order) else float(
        "nan"
    )

    delivered = orders[orders["order_status"].str.lower() == "delivered"].copy()
    delivered["deliv"] = pd.to_datetime(
        delivered["order_delivered_customer_date"], errors="coerce"
    )
    delivered["est"] = pd.to_datetime(
        delivered["order_estimated_delivery_date"], errors="coerce"
    )
    delivered["purchase"] = pd.to_datetime(
        delivered["order_purchase_timestamp"], errors="coerce"
    )
    both = delivered.dropna(subset=["deliv", "est"])
    late = both["deliv"] > both["est"]
    on_time = int((~late).sum())
    late_n = int(late.sum())
    denom = on_time + late_n
    on_time_rate = on_time / denom if denom else float("nan")
    late_rate = late_n / denom if denom else float("nan")

    with_deliv = delivered.dropna(subset=["deliv", "purchase"])
    delivery_days = (with_deliv["deliv"] - with_deliv["purchase"]).dt.total_seconds() / 86400.0
    avg_days = float(delivery_days.mean()) if len(delivery_days) else float("nan")

    unique_customers = int(customers["customer_unique_id"].nunique())
    orders_per_customer = customers.groupby("customer_unique_id").size()
    repeat_customers = int((orders_per_customer > 1).sum())
    repeat_rate = (
        repeat_customers / unique_customers if unique_customers else float("nan")
    )

    orders_without_items = int((~orders["order_id"].isin(items["order_id"])).sum())
    orders_without_payments = int(
        (~orders["order_id"].isin(payments["order_id"])).sum()
    )

    return BusinessMetrics(
        total_orders=total_orders,
        merchandise_revenue=round(merchandise, 2),
        freight_total=round(freight, 2),
        order_value=round(order_value, 2),
        payment_total=round(payment_total, 2),
        average_order_value=round(aov, 4),
        avg_review_score_all_reviews=round(avg_all, 6),
        avg_review_score_one_per_order=round(avg_one, 6),
        delivered_orders=int(len(delivered)),
        on_time_deliveries=on_time,
        late_deliveries=late_n,
        on_time_rate=round(on_time_rate, 6),
        late_rate=round(late_rate, 6),
        avg_delivery_days=round(avg_days, 4),
        unique_customers=unique_customers,
        repeat_customers=repeat_customers,
        repeat_customer_rate=round(repeat_rate, 6),
        orders_without_items=orders_without_items,
        orders_without_payments=orders_without_payments,
        payment_minus_order_value=round(payment_total - order_value, 2),
    )


def detect_join_inflation(
    left: pd.DataFrame,
    right: pd.DataFrame,
    on: str,
    measure_col: str,
) -> dict[str, float]:
    """Compare sum(measure) before vs after a naive join (fan-out detector)."""
    base = float(pd.to_numeric(left[measure_col], errors="coerce").sum())
    merged = left.merge(right, on=on, how="left", suffixes=("", "_r"))
    inflated = float(pd.to_numeric(merged[measure_col], errors="coerce").sum())
    return {
        "base_sum": round(base, 2),
        "post_join_sum": round(inflated, 2),
        "inflation": round(inflated - base, 2),
        "inflated": abs(inflated - base) > 0.01,
    }
