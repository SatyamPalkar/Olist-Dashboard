"""Generate a structured data-quality report from raw CSVs (+ optional DB)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from tests.helpers.contracts import EXPECTED_COLUMNS, MONEY_TOLERANCE, PRIMARY_KEYS, RAW_FILES
from tests.helpers.metrics import compute_business_metrics, detect_join_inflation
from tests.helpers.raw_loader import load_raw, null_report


def _pk_duplicate_stats(entity: str, df: pd.DataFrame) -> dict[str, Any]:
    keys = PRIMARY_KEYS.get(entity)
    if not keys:
        return {
            "keys": None,
            "duplicate_rows": None,
            "note": "No declared unique key (e.g. geolocation)",
        }
    dup_mask = df.duplicated(subset=keys, keep=False)
    return {
        "keys": keys,
        "duplicate_row_count": int(dup_mask.sum()),
        "duplicate_key_groups": int(df.loc[dup_mask].groupby(keys).ngroups)
        if dup_mask.any()
        else 0,
        "is_unique": not bool(df.duplicated(subset=keys).any()),
    }


def build_raw_quality_report() -> dict[str, Any]:
    entities: dict[str, Any] = {}
    total_records = 0
    for entity in RAW_FILES:
        df = load_raw(entity)
        total_records += len(df)
        entities[entity] = {
            "file": RAW_FILES[entity],
            "rows": int(len(df)),
            "columns": list(df.columns),
            "expected_columns_ok": list(df.columns)[: len(EXPECTED_COLUMNS[entity])]
            == EXPECTED_COLUMNS[entity]
            or set(EXPECTED_COLUMNS[entity]).issubset(df.columns),
            "null_counts": null_report(df),
            "primary_key": _pk_duplicate_stats(entity, df),
        }

    orders = load_raw("orders")
    items = load_raw("order_items")
    payments = load_raw("order_payments")
    reviews = load_raw("order_reviews")
    customers = load_raw("customers")
    products = load_raw("products")
    sellers = load_raw("sellers")
    translation = load_raw("category_translation")

    referential = {
        "items_orphan_orders": int((~items["order_id"].isin(orders["order_id"])).sum()),
        "payments_orphan_orders": int(
            (~payments["order_id"].isin(orders["order_id"])).sum()
        ),
        "reviews_orphan_orders": int(
            (~reviews["order_id"].isin(orders["order_id"])).sum()
        ),
        "orders_orphan_customers": int(
            (~orders["customer_id"].isin(customers["customer_id"])).sum()
        ),
        "items_orphan_products": int(
            (~items["product_id"].isin(products["product_id"])).sum()
        ),
        "items_orphan_sellers": int(
            (~items["seller_id"].isin(sellers["seller_id"])).sum()
        ),
        "products_unmapped_categories": int(
            products["product_category_name"]
            .dropna()
            .pipe(lambda s: (~s.isin(translation["product_category_name"])).sum())
        ),
    }

    metrics = compute_business_metrics(orders, items, payments, reviews, customers)

    # Double-counting / fan-out probes
    item_vs_pay = detect_join_inflation(
        items.assign(_m=items["price"]),
        payments,
        on="order_id",
        measure_col="_m",
    )
    item_vs_rev = detect_join_inflation(
        items.assign(_m=items["price"]),
        reviews,
        on="order_id",
        measure_col="_m",
    )

    multiplicity = {
        "orders_with_multiple_items": int(
            (items.groupby("order_id").size() > 1).sum()
        ),
        "orders_with_multiple_payments": int(
            (payments.groupby("order_id").size() > 1).sum()
        ),
        "orders_with_multiple_reviews": int(
            (reviews.groupby("order_id").size() > 1).sum()
        ),
        "max_items_per_order": int(items.groupby("order_id").size().max()),
        "max_payments_per_order": int(payments.groupby("order_id").size().max()),
        "max_reviews_per_order": int(reviews.groupby("order_id").size().max()),
        "duplicate_review_id_rows": int(reviews["review_id"].duplicated().sum()),
        "naive_join_items_x_payments_inflation": item_vs_pay,
        "naive_join_items_x_reviews_inflation": item_vs_rev,
    }

    recon_diff = abs(metrics.payment_minus_order_value)
    critical_ref_ok = all(
        referential[k] == 0
        for k in (
            "items_orphan_orders",
            "payments_orphan_orders",
            "reviews_orphan_orders",
            "orders_orphan_customers",
            "items_orphan_products",
            "items_orphan_sellers",
        )
    )

    # Known accepted exceptions (quantified)
    known_exceptions = [
        {
            "id": "KX-001",
            "issue": "review_id is not unique in source",
            "count": multiplicity["duplicate_review_id_rows"],
            "severity": "Use surrogate review_sk in staging/analytics",
        },
        {
            "id": "KX-002",
            "issue": "payment_total ≠ merchandise + freight",
            "difference_brl": metrics.payment_minus_order_value,
            "tolerance_note": "Vouchers/splits/order gaps; not treated as load failure",
        },
        {
            "id": "KX-003",
            "issue": "orders without order_items",
            "count": metrics.orders_without_items,
            "disposition": "Typically canceled/unavailable; retain in fact_orders",
        },
        {
            "id": "KX-004",
            "issue": "products missing English category translation",
            "count": referential["products_unmapped_categories"],
            "disposition": "Label unmapped explicitly; do not drop products",
        },
        {
            "id": "KX-005",
            "issue": "geolocation many rows per zip prefix",
            "disposition": "Aggregate to centroid in staging.stg_geolocation",
        },
    ]

    status = "PASS" if critical_ref_ok else "FAIL"
    if recon_diff > MONEY_TOLERANCE:
        # Documented difference — warn, do not auto-fail overall raw integrity
        overall = "PASS_WITH_EXCEPTIONS" if status == "PASS" else status
    else:
        overall = status

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_records_tested": total_records,
        "entity_count": len(entities),
        "entities": entities,
        "referential_integrity": referential,
        "multiplicity_and_double_counting": multiplicity,
        "business_metrics_python": metrics.to_dict(),
        "known_exceptions": known_exceptions,
        "overall_data_quality_status": overall,
        "summary": {
            "critical_referential_ok": critical_ref_ok,
            "payment_vs_order_value_diff_brl": metrics.payment_minus_order_value,
            "null_columns_with_nulls": sum(
                1 for e in entities.values() if e["null_counts"]
            ),
        },
    }


def write_report(
    report: dict[str, Any],
    json_path: Path,
    md_path: Path | None = None,
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if md_path is None:
        return
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_to_markdown(report), encoding="utf-8")


def _to_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    m = report["business_metrics_python"]
    lines = [
        "# Data Quality Report",
        "",
        f"**Generated (UTC):** {report['generated_at']}",
        f"**Overall status:** `{report['overall_data_quality_status']}`",
        f"**Total records tested:** {report['total_records_tested']:,}",
        "",
        "## Summary",
        "",
        f"- Critical referential integrity OK: **{s['critical_referential_ok']}**",
        f"- Entities with nulls: {s['null_columns_with_nulls']}",
        f"- Payment − order_value (BRL): {s['payment_vs_order_value_diff_brl']}",
        "",
        "## Business metrics (Python oracle)",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total orders | {m['total_orders']:,} |",
        f"| Merchandise revenue | {m['merchandise_revenue']:,.2f} |",
        f"| Freight total | {m['freight_total']:,.2f} |",
        f"| Order value (merch+freight) | {m['order_value']:,.2f} |",
        f"| Payment total | {m['payment_total']:,.2f} |",
        f"| AOV | {m['average_order_value']:,.4f} |",
        f"| Avg review (all rows) | {m['avg_review_score_all_reviews']:.4f} |",
        f"| Avg review (1/order) | {m['avg_review_score_one_per_order']:.4f} |",
        f"| On-time rate | {m['on_time_rate']:.4%} |",
        f"| Late rate | {m['late_rate']:.4%} |",
        f"| Avg delivery days | {m['avg_delivery_days']:.2f} |",
        f"| Repeat customer rate | {m['repeat_customer_rate']:.4%} |",
        "",
        "## Referential integrity",
        "",
    ]
    for k, v in report["referential_integrity"].items():
        lines.append(f"- `{k}`: {v}")
    lines.extend(["", "## Known exceptions", ""])
    for ex in report["known_exceptions"]:
        lines.append(f"- **{ex['id']}** — {ex['issue']}: `{json.dumps({k:v for k,v in ex.items() if k not in ('id','issue')})}`")
    lines.extend(
        [
            "",
            "## Double-counting probes",
            "",
            "Naive joins of items→payments or items→reviews **inflate** merchandise sums.",
            "Warehouse facts pre-aggregate before join (see `analytics.fact_orders`).",
            "",
            f"- Orders with multiple items: {report['multiplicity_and_double_counting']['orders_with_multiple_items']}",
            f"- Orders with multiple payments: {report['multiplicity_and_double_counting']['orders_with_multiple_payments']}",
            f"- Orders with multiple reviews: {report['multiplicity_and_double_counting']['orders_with_multiple_reviews']}",
            f"- Duplicate `review_id` rows: {report['multiplicity_and_double_counting']['duplicate_review_id_rows']}",
            "",
            "See also `docs/known_data_limitations.md`.",
            "",
        ]
    )
    return "\n".join(lines)
