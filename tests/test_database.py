"""Database validation — PK/FK integrity, required fields, constraints, fact grain.

Integration tests skip automatically when PostgreSQL / warehouse is unavailable.
"""

from __future__ import annotations

import pytest

from tests.helpers.contracts import ANALYTICS_DIMS, ANALYTICS_FACTS, STAGING_TABLES, WAREHOUSE_SCHEMAS
from tests.helpers import db as db_helper

pytestmark = [pytest.mark.integration]


@pytest.mark.parametrize("schema", WAREHOUSE_SCHEMAS)
def test_warehouse_schemas_exist(schema: str) -> None:
    exists = db_helper.scalar(
        "SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = %s)",
        (schema,),
    )
    assert exists, f"Missing schema: {schema}"


@pytest.mark.parametrize("table", STAGING_TABLES)
def test_staging_tables_exist(table: str) -> None:
    assert db_helper.table_exists("staging", table), f"Missing staging.{table}"


@pytest.mark.parametrize("table", ANALYTICS_DIMS + ANALYTICS_FACTS)
def test_analytics_tables_exist(table: str) -> None:
    assert db_helper.table_exists("analytics", table), f"Missing analytics.{table}"


@pytest.mark.requires_warehouse
def test_fact_orders_pk_unique() -> None:
    dups = db_helper.scalar(
        """
        SELECT COUNT(*) FROM (
            SELECT order_id FROM analytics.fact_orders
            GROUP BY order_id HAVING COUNT(*) > 1
        ) t
        """
    )
    assert int(dups) == 0


@pytest.mark.requires_warehouse
def test_fact_order_items_grain_unique() -> None:
    dups = db_helper.scalar(
        """
        SELECT COUNT(*) FROM (
            SELECT order_id, order_item_id
            FROM analytics.fact_order_items
            GROUP BY order_id, order_item_id
            HAVING COUNT(*) > 1
        ) t
        """
    )
    assert int(dups) == 0


@pytest.mark.requires_warehouse
def test_fact_payments_grain_unique() -> None:
    dups = db_helper.scalar(
        """
        SELECT COUNT(*) FROM (
            SELECT order_id, payment_sequential
            FROM analytics.fact_payments
            GROUP BY order_id, payment_sequential
            HAVING COUNT(*) > 1
        ) t
        """
    )
    assert int(dups) == 0


@pytest.mark.requires_warehouse
def test_dim_customers_unique_on_customer_unique_id() -> None:
    dups = db_helper.scalar(
        """
        SELECT COUNT(*) FROM (
            SELECT customer_unique_id FROM analytics.dim_customers
            GROUP BY customer_unique_id HAVING COUNT(*) > 1
        ) t
        """
    )
    assert int(dups) == 0


@pytest.mark.requires_warehouse
def test_fact_order_items_fk_to_fact_orders() -> None:
    orphans = db_helper.scalar(
        """
        SELECT COUNT(*)
        FROM analytics.fact_order_items i
        LEFT JOIN analytics.fact_orders o ON o.order_key = i.order_key
        WHERE o.order_key IS NULL
        """
    )
    assert int(orphans) == 0


@pytest.mark.requires_warehouse
def test_fact_payments_fk_to_fact_orders() -> None:
    orphans = db_helper.scalar(
        """
        SELECT COUNT(*)
        FROM analytics.fact_payments p
        LEFT JOIN analytics.fact_orders o ON o.order_key = p.order_key
        WHERE o.order_key IS NULL
        """
    )
    assert int(orphans) == 0


@pytest.mark.requires_warehouse
def test_fact_reviews_fk_to_fact_orders() -> None:
    orphans = db_helper.scalar(
        """
        SELECT COUNT(*)
        FROM analytics.fact_order_reviews r
        LEFT JOIN analytics.fact_orders o ON o.order_key = r.order_key
        WHERE o.order_key IS NULL
        """
    )
    assert int(orphans) == 0


@pytest.mark.requires_warehouse
def test_fact_orders_customer_fk() -> None:
    orphans = db_helper.scalar(
        """
        SELECT COUNT(*)
        FROM analytics.fact_orders f
        LEFT JOIN analytics.dim_customers c ON c.customer_key = f.customer_key
        WHERE c.customer_key IS NULL
        """
    )
    assert int(orphans) == 0


@pytest.mark.requires_warehouse
def test_required_fields_fact_orders() -> None:
    bad = db_helper.scalar(
        """
        SELECT COUNT(*) FROM analytics.fact_orders
        WHERE order_id IS NULL
           OR customer_key IS NULL
           OR purchase_date_key IS NULL
           OR order_status IS NULL
        """
    )
    assert int(bad) == 0


@pytest.mark.requires_warehouse
def test_review_score_check_constraint() -> None:
    bad = db_helper.scalar(
        """
        SELECT COUNT(*) FROM analytics.fact_order_reviews
        WHERE review_score < 1 OR review_score > 5
        """
    )
    assert int(bad) == 0


@pytest.mark.requires_warehouse
def test_fact_orders_grain_is_one_row_per_order() -> None:
    rows = int(db_helper.scalar("SELECT COUNT(*) FROM analytics.fact_orders"))
    distinct = int(
        db_helper.scalar("SELECT COUNT(DISTINCT order_id) FROM analytics.fact_orders")
    )
    assert rows == distinct


@pytest.mark.requires_warehouse
def test_fact_orders_preaggregated_matches_item_sum() -> None:
    """merchandise_sales on fact_orders must equal SUM(price) on fact_order_items."""
    diff = db_helper.scalar(
        """
        WITH oi AS (
            SELECT order_id, SUM(price) AS merch
            FROM analytics.fact_order_items
            GROUP BY order_id
        )
        SELECT COALESCE(SUM(ABS(f.merchandise_sales - COALESCE(oi.merch, 0))), 0)
        FROM analytics.fact_orders f
        LEFT JOIN oi ON oi.order_id = f.order_id
        """
    )
    assert float(diff) < 0.05


@pytest.mark.requires_warehouse
def test_no_silent_discard_orders_without_items() -> None:
    """Orders with zero items should still appear in fact_orders (item_count = 0)."""
    zero_item_orders = int(
        db_helper.scalar(
            "SELECT COUNT(*) FROM analytics.fact_orders WHERE item_count = 0"
        )
    )
    # Source has ~775; allow load filters but must not be zero if staging kept them
    stg_zero = int(
        db_helper.scalar(
            """
            SELECT COUNT(*) FROM staging.stg_orders o
            WHERE NOT EXISTS (
                SELECT 1 FROM staging.stg_order_items i WHERE i.order_id = o.order_id
            )
            """
        )
    )
    assert zero_item_orders == stg_zero
