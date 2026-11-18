"""Business Analyst KPI analysis on Olist raw CSVs. Outputs JSON summary for documentation."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import numpy as np

RAW = Path("data/raw")
OUT = Path("docs/_analysis_cache.json")


def load():
    customers = pd.read_csv(RAW / "olist_customers_dataset.csv")
    orders = pd.read_csv(
        RAW / "olist_orders_dataset.csv",
        parse_dates=[
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    )
    items = pd.read_csv(
        RAW / "olist_order_items_dataset.csv",
        parse_dates=["shipping_limit_date"],
    )
    payments = pd.read_csv(RAW / "olist_order_payments_dataset.csv")
    reviews = pd.read_csv(RAW / "olist_order_reviews_dataset.csv")
    products = pd.read_csv(RAW / "olist_products_dataset.csv")
    sellers = pd.read_csv(RAW / "olist_sellers_dataset.csv")
    cat_tr = pd.read_csv(RAW / "product_category_name_translation.csv")
    return customers, orders, items, payments, reviews, products, sellers, cat_tr


def main():
    customers, orders, items, payments, reviews, products, sellers, cat_tr = load()

    # Delivered / completed commercial base: use delivered orders for most commercial KPIs
    delivered = orders[orders["order_status"] == "delivered"].copy()
    # Merchandise revenue & freight from order items (join delivered)
    items_d = items.merge(delivered[["order_id"]], on="order_id", how="inner")
    merch_rev = float(items_d["price"].sum())
    freight = float(items_d["freight_value"].sum())
    total_order_value = merch_rev + freight
    n_orders = items_d["order_id"].nunique()
    aov = total_order_value / n_orders if n_orders else None

    # Monthly revenue (merchandise) by purchase month
    order_dates = delivered.set_index("order_id")["order_purchase_timestamp"]
    items_d = items_d.copy()
    items_d["purchase_ts"] = items_d["order_id"].map(order_dates)
    items_d["year_month"] = items_d["purchase_ts"].dt.to_period("M").astype(str)
    monthly = (
        items_d.groupby("year_month")
        .agg(merchandise_revenue=("price", "sum"), orders=("order_id", "nunique"))
        .reset_index()
        .sort_values("year_month")
    )
    monthly["mom_growth_pct"] = monthly["merchandise_revenue"].pct_change() * 100
    # Exclude incomplete edge months if tiny
    monthly_records = monthly.to_dict(orient="records")

    # Customers
    cust_orders = delivered.merge(
        customers[["customer_id", "customer_unique_id", "customer_state", "customer_city"]],
        on="customer_id",
        how="left",
    )
    unique_customers = int(cust_orders["customer_unique_id"].nunique())
    orders_per_cust = (
        cust_orders.groupby("customer_unique_id")["order_id"].nunique().rename("n_orders")
    )
    repeat_customers = int((orders_per_cust >= 2).sum())
    repeat_rate = repeat_customers / unique_customers * 100 if unique_customers else None
    avg_orders_per_customer = float(orders_per_cust.mean())

    # Reviews (one score per order — take mean if multiple)
    rev_order = reviews.groupby("order_id")["review_score"].mean().reset_index()
    delivered_rev = delivered.merge(rev_order, on="order_id", how="left")
    avg_review = float(delivered_rev["review_score"].mean())

    # Delivery performance
    deliv = delivered.dropna(
        subset=["order_delivered_customer_date", "order_estimated_delivery_date", "order_purchase_timestamp"]
    ).copy()
    deliv["delivery_days"] = (
        deliv["order_delivered_customer_date"] - deliv["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400
    deliv["estimated_days"] = (
        deliv["order_estimated_delivery_date"] - deliv["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400
    deliv["late"] = deliv["order_delivered_customer_date"] > deliv["order_estimated_delivery_date"]
    deliv["est_vs_actual_days"] = (
        deliv["order_delivered_customer_date"] - deliv["order_estimated_delivery_date"]
    ).dt.total_seconds() / 86400
    avg_delivery_days = float(deliv["delivery_days"].mean())
    late_pct = float(deliv["late"].mean() * 100)
    avg_est_vs_actual = float(deliv["est_vs_actual_days"].mean())  # negative = early

    # Late by state
    deliv_c = deliv.merge(
        customers[["customer_id", "customer_state"]], on="customer_id", how="left"
    )
    late_by_state = (
        deliv_c.groupby("customer_state")
        .agg(
            orders=("order_id", "count"),
            late_pct=("late", "mean"),
            avg_delivery_days=("delivery_days", "mean"),
            avg_review=("order_id", "count"),  # placeholder overwritten below
        )
        .reset_index()
    )
    # attach reviews
    deliv_c2 = deliv_c.merge(rev_order, on="order_id", how="left")
    late_by_state = (
        deliv_c2.groupby("customer_state")
        .agg(
            orders=("order_id", "count"),
            late_pct=("late", lambda s: s.mean() * 100),
            avg_delivery_days=("delivery_days", "mean"),
            avg_review=("review_score", "mean"),
        )
        .reset_index()
        .sort_values("orders", ascending=False)
    )
    late_by_state_top = late_by_state.head(15).to_dict(orient="records")
    late_by_state_worst = (
        late_by_state[late_by_state["orders"] >= 200]
        .sort_values("late_pct", ascending=False)
        .head(10)
        .to_dict(orient="records")
    )

    # Late vs review association (correlation, not causation)
    late_review_corr = float(
        deliv_c2.dropna(subset=["review_score"])[["late", "review_score"]]
        .assign(late=lambda d: d["late"].astype(int))
        .corr()
        .loc["late", "review_score"]
    )
    review_late = float(deliv_c2.loc[deliv_c2["late"], "review_score"].mean())
    review_ontime = float(deliv_c2.loc[~deliv_c2["late"], "review_score"].mean())

    # Categories
    products_en = products.merge(cat_tr, on="product_category_name", how="left")
    products_en["category"] = products_en["product_category_name_english"].fillna(
        products_en["product_category_name"]
    ).fillna("unknown")
    items_cat = items_d.merge(
        products_en[["product_id", "category"]], on="product_id", how="left"
    )
    cat_perf = (
        items_cat.groupby("category")
        .agg(
            merchandise_revenue=("price", "sum"),
            freight=("freight_value", "sum"),
            order_items=("order_item_id", "count"),
            orders=("order_id", "nunique"),
        )
        .reset_index()
    )
    cat_perf["total_order_value"] = cat_perf["merchandise_revenue"] + cat_perf["freight"]
    cat_perf["revenue_share_pct"] = (
        cat_perf["merchandise_revenue"] / cat_perf["merchandise_revenue"].sum() * 100
    )
    cat_perf["avg_freight_per_item"] = cat_perf["freight"] / cat_perf["order_items"]
    cat_perf["freight_to_price_ratio"] = cat_perf["freight"] / cat_perf["merchandise_revenue"]
    top_cats = cat_perf.sort_values("merchandise_revenue", ascending=False).head(15)
    bottom_cats = cat_perf.sort_values("merchandise_revenue", ascending=True).head(10)
    high_freight = cat_perf.sort_values("freight_to_price_ratio", ascending=False).head(10)

    # Category monthly for decline detection (use last 6 complete months with volume)
    items_cat["year_month"] = items_cat["year_month"]
    cat_month = (
        items_cat.groupby(["category", "year_month"])["price"]
        .sum()
        .reset_index(name="revenue")
    )
    # Focus on months with substantial platform volume
    month_totals = monthly.set_index("year_month")["merchandise_revenue"]
    valid_months = month_totals[month_totals >= month_totals.quantile(0.2)].index.tolist()
    # Compare first half vs second half of valid window for top categories
    valid_sorted = sorted(valid_months)
    if len(valid_sorted) >= 6:
        first = valid_sorted[: len(valid_sorted) // 2]
        second = valid_sorted[len(valid_sorted) // 2 :]
    else:
        first, second = valid_sorted[: max(1, len(valid_sorted) // 2)], valid_sorted[
            max(1, len(valid_sorted) // 2) :
        ]

    def period_rev(cats_df, months):
        return (
            cats_df[cats_df["year_month"].isin(months)]
            .groupby("category")["revenue"]
            .sum()
        )

    r1 = period_rev(cat_month, first)
    r2 = period_rev(cat_month, second)
    decline = pd.DataFrame({"period1": r1, "period2": r2}).fillna(0)
    decline["change_pct"] = (decline["period2"] - decline["period1"]) / decline["period1"].replace(
        0, np.nan
    ) * 100
    # Only categories with meaningful period1 revenue
    decline = decline[decline["period1"] >= 50000].sort_values("change_pct")
    declining = decline.head(10).reset_index().to_dict(orient="records")
    growing = decline.sort_values("change_pct", ascending=False).head(10).reset_index().to_dict(
        orient="records"
    )

    # Revenue by region (customer state)
    items_reg = items_d.merge(
        delivered[["order_id", "customer_id"]], on="order_id", how="left"
    ).merge(
        customers[["customer_id", "customer_state"]], on="customer_id", how="left"
    )
    by_state = (
        items_reg.groupby("customer_state")
        .agg(
            merchandise_revenue=("price", "sum"),
            freight=("freight_value", "sum"),
            orders=("order_id", "nunique"),
        )
        .reset_index()
        .sort_values("merchandise_revenue", ascending=False)
    )
    by_state["revenue_share_pct"] = (
        by_state["merchandise_revenue"] / by_state["merchandise_revenue"].sum() * 100
    )
    top_states = by_state.head(12).to_dict(orient="records")

    # Customer value segments by total merchandise spend
    cust_spend = (
        items_d.merge(delivered[["order_id", "customer_id"]], on="order_id")
        .merge(customers[["customer_id", "customer_unique_id"]], on="customer_id")
        .groupby("customer_unique_id")
        .agg(merchandise_revenue=("price", "sum"), orders=("order_id", "nunique"))
        .reset_index()
    )
    cust_spend["segment"] = pd.qcut(
        cust_spend["merchandise_revenue"],
        q=4,
        labels=["Low", "Medium", "High", "Top"],
        duplicates="drop",
    )
    segments = (
        cust_spend.groupby("segment", observed=True)
        .agg(
            customers=("customer_unique_id", "count"),
            merchandise_revenue=("merchandise_revenue", "sum"),
            avg_spend=("merchandise_revenue", "mean"),
            avg_orders=("orders", "mean"),
        )
        .reset_index()
    )
    segments["revenue_share_pct"] = (
        segments["merchandise_revenue"] / segments["merchandise_revenue"].sum() * 100
    )
    segments_rec = segments.to_dict(orient="records")

    # Date range
    date_min = str(delivered["order_purchase_timestamp"].min())
    date_max = str(delivered["order_purchase_timestamp"].max())

    # Overall MoM for recent months
    recent_monthly = monthly.tail(8).to_dict(orient="records")

    result = {
        "scope": {
            "dataset": "Olist Brazilian E-Commerce Public Dataset",
            "order_status_filter": "delivered",
            "purchase_date_min": date_min,
            "purchase_date_max": date_max,
            "delivered_orders": int(n_orders),
            "unique_customers": unique_customers,
            "note": (
                "Commercial KPIs use merchandise price and freight from order_items "
                "for delivered orders only. Revenue is GMV/merchandise sales, not profit."
            ),
        },
        "commercial": {
            "merchandise_revenue": merch_rev,
            "freight_charges": freight,
            "total_order_value": total_order_value,
            "average_order_value": aov,
            "monthly_revenue": monthly_records,
            "recent_monthly": recent_monthly,
        },
        "customer": {
            "unique_customers": unique_customers,
            "repeat_customers": repeat_customers,
            "repeat_customer_rate_pct": repeat_rate,
            "orders_per_customer": avg_orders_per_customer,
            "average_review_score": avg_review,
            "segments": segments_rec,
        },
        "operational": {
            "average_delivery_days": avg_delivery_days,
            "late_delivery_pct": late_pct,
            "avg_actual_minus_estimated_days": avg_est_vs_actual,
            "late_by_state_volume_top": late_by_state_top,
            "late_by_state_worst_min200": late_by_state_worst,
            "review_score_late": review_late,
            "review_score_ontime": review_ontime,
            "late_review_correlation": late_review_corr,
        },
        "product": {
            "top_categories": top_cats.to_dict(orient="records"),
            "bottom_categories": bottom_cats.to_dict(orient="records"),
            "high_freight_ratio_categories": high_freight.to_dict(orient="records"),
            "decline_comparison_periods": {"period1_months": first, "period2_months": second},
            "declining_categories": declining,
            "growing_categories": growing,
        },
        "geography": {"top_states_by_revenue": top_states},
    }

    # JSON-safe floats
    def clean(o):
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items()}
        if isinstance(o, list):
            return [clean(v) for v in o]
        if isinstance(o, (np.floating, float)):
            if np.isnan(o) or np.isinf(o):
                return None
            return float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, pd.Timestamp):
            return str(o)
        return o

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(clean(result), f, indent=2)
    print(f"Wrote {OUT}")
    print(
        json.dumps(
            {
                "merchandise_revenue": merch_rev,
                "freight": freight,
                "aov": aov,
                "unique_customers": unique_customers,
                "repeat_rate": repeat_rate,
                "avg_delivery_days": avg_delivery_days,
                "late_pct": late_pct,
                "avg_review": avg_review,
                "top_cat": top_cats.iloc[0]["category"] if len(top_cats) else None,
                "top_state": by_state.iloc[0]["customer_state"] if len(by_state) else None,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
