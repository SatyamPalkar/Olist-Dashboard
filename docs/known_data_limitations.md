# Known data limitations (Olist)

Quantified against local `data/raw/` on 2026-11-18.  
**Rule:** do not change source files to force tests to pass. Exceptions are documented here.

| ID | Limitation | Evidence | Disposition |
|----|------------|----------|-------------|
| KX-001 | `review_id` is **not unique** | 814 duplicate `review_id` rows; 547 orders with >1 review | Staging uses surrogate `review_sk`; analytics keeps all review rows |
| KX-002 | `SUM(payment_value)` ≠ `SUM(price)+SUM(freight_value)` | Diff ≈ **R$ 160,628.98** | Expected (vouchers, splits, orders w/o items). Report both measures; do not coerce equality |
| KX-003 | Orders without items | **775** orders | Mostly canceled/unavailable; keep in `fact_orders` with `item_count = 0` |
| KX-004 | Orders without payments | **1** order | Retain; payment measures null/0 |
| KX-005 | Product categories without EN translation | **13** product rows | Label unmapped; never drop products |
| KX-006 | Geolocation many rows per zip | 1,000,163 rows → 19,015 zips | Aggregate centroid in `staging.stg_geolocation` |
| KX-007 | `customer_id` is order-scoped | 99,441 `customer_id` = order count; 96,096 unique people | Use `customer_unique_id` for repeat-buyer KPIs |
| KX-008 | Nullable delivery timestamps | e.g. 2,965 null `order_delivered_customer_date` | Delivery KPIs only where both actual + estimated exist |
| KX-009 | Schema naming drift | Orchestrator ADR-003: `staging`/`dw`; SQL Architect DDL: `raw`/`staging`/`analytics` | QA tests target **implemented** SQL Architect schemas; Orchestrator ADR update pending |

## Double-counting risks (must not ship in measures)

| Join | Effect |
|------|--------|
| `order_items` ⨯ `order_payments` on `order_id` | Inflates merchandise / freight |
| `order_items` ⨯ `order_reviews` on `order_id` | Inflates merchandise |
| `fact_order_items` ⨯ `fact_payments` without pre-agg | Inflates revenue |

**Correct pattern:** pre-aggregate to order grain (as in `database/marts/fact_orders.sql`), or use separate facts without cross-joining at line grain.

## Metric definition freeze

KPI definitions live in `docs/requirements.md` and `analytics.fact_*` comments.  
QA must not alter definitions independently — coordinate with SQL Architect + Business Analyst.
