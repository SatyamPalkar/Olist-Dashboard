# Database Schema Documentation

## Layers

| Schema | Role | Consumers |
|--------|------|-----------|
| `raw` | Landing — immutable-ish dump of CSVs | Data Engineer |
| `staging` | Typed, cleaned entities | SQL transforms only |
| `analytics` | Star schema + views for BI | Power BI, analysts |

## Proposal validation (vs Olist source)

| Proposed object | Verdict | Grain / notes |
|-----------------|---------|---------------|
| fact_orders | **Keep** | 1 row / `order_id`. Money pre-aggregated. |
| fact_order_items | **Keep** | 1 row / `order_id` + `order_item_id`. Primary revenue fact. |
| fact_payments | **Keep** | 1 row / `order_id` + `payment_sequential`. |
| fact_order_reviews | **Keep** | 1 row / review instance (surrogate). |
| dim_customers | **Keep** | Keyed on `customer_unique_id` (not `customer_id`). |
| dim_products | **Keep** | Includes EN category. |
| dim_sellers | **Keep** | Linked to geography. |
| dim_date | **Keep** | Generated 2016–2018. |
| dim_geography | **Keep** | Grain = zip_code_prefix (+ state region). |

### Slowly changing dimensions

All dimensions are **SCD Type 1** (overwrite). Justification: public dataset is a fixed historical snapshot with no change history.

Surrogate keys (`*_key BIGSERIAL`) are used for Power BI relationships; natural keys kept as UNIQUE business keys.

## Fact table details

### fact_orders

| Attribute | Type | Description |
|-----------|------|-------------|
| order_key | BIGSERIAL PK | Surrogate |
| order_id | TEXT UK | Natural key |
| customer_key | FK → dim_customers | Unique customer |
| purchase_date_key | FK → dim_date | Order date |
| merchandise_sales | NUMERIC | SUM(price) |
| freight_charges | NUMERIC | SUM(freight) |
| order_value | NUMERIC | merch + freight |
| payment_amount | NUMERIC | SUM(payments) |
| delivery_days | NUMERIC | Purchase → delivery |
| is_late_delivery | BOOLEAN | vs estimate |

### fact_order_items

| Attribute | Type | Description |
|-----------|------|-------------|
| order_item_key | BIGSERIAL PK | Surrogate |
| order_id + order_item_id | UK | Natural composite |
| product_key / seller_key | FK | Dimensions |
| price | NUMERIC | Line merchandise sales |
| freight_value | NUMERIC | Line freight |
| item_total | NUMERIC | price + freight |

### fact_payments / fact_order_reviews

See DDL comments in `schemas/03_analytics_tables.sql`.

## Indexing strategy

Indexes target:

- Fact FK columns used in Power BI joins (`purchase_date_key`, `product_key`, `seller_key`, `customer_key`)
- Common filters (`order_status`, `payment_type`, `review_score`, `state`)
- Staging build join keys

See `schemas/04_indexes.sql`. Validate with `scripts/explain_analyze_samples.sql`.

## Materialised views

| Object | Purpose | Refresh |
|--------|---------|---------|
| `mv_monthly_sales` | Fast monthly KPI | After mart rebuild |
| `mv_category_monthly_sales` | Category trends | After mart rebuild |

Use MVs only for stable, high-frequency aggregates — not for every view.

## Constraints

- PKs / UKs on all analytics tables
- FKs from facts → dims (and order-child facts → fact_orders)
- CHECK on review_score 1–5
- Schema changes wrapped in transactions

## Rerun safety

- DDL uses `DROP IF EXISTS` / `CREATE IF NOT EXISTS` patterns
- Transforms use `TRUNCATE` + `INSERT` (or `ON CONFLICT DO NOTHING` where noted)
- Seeds truncate and reload
