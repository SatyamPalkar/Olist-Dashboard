# KPI & Metric Definitions

## Money measures — do not confuse

| Term | Definition | Source grain | Notes |
|------|------------|--------------|-------|
| **Merchandise sales** | `SUM(price)` | order item | Canonical **revenue** for product/category/seller analysis |
| **Freight charges** | `SUM(freight_value)` | order item | Shipping charged to customer |
| **Order value (GMV)** | merchandise + freight | order or item | Full customer charge for goods+shipping |
| **Payment amount** | `SUM(payment_value)` | payment | Cash collected; may differ (vouchers, splits) |
| **Revenue** | = Merchandise sales | — | Label used in reports for `price` totals |
| **Profit** | **Not available** | — | No COGS / cost fields in Olist public data. **Never label revenue as profit.** |

## Double-counting rules

1. **Never** join `fact_order_items` to `fact_payments` at line grain for summing money — fan-out multiplies amounts.
2. For order-level money, use `fact_orders` (pre-aggregated) or aggregate items/payments **separately** then join.
3. Order counts: `COUNT(DISTINCT order_id)` when querying from item grain.
4. Customer counts / retention: use `customer_unique_id` / `dim_customers.customer_key`, **not** `customer_id`.

## KPI catalogue

| # | KPI | Formula | Primary object | Filters |
|---|-----|---------|----------------|---------|
| 1 | Total sales by month | `SUM(merchandise_sales)` by `year_month` | `vw_sales_by_month` | `is_canceled = FALSE` |
| 2 | Revenue by category | `SUM(price)` by English category | `vw_revenue_by_category` | non-canceled |
| 3 | Top 10 products | `RANK()` on `SUM(price)` | `vw_top_10_products` | non-canceled |
| 4 | Sales by geography | `SUM(merchandise_sales)` by customer state/region | `vw_sales_by_geography` | non-canceled |
| 5 | Average order value | `AVG(order_value)` at order grain | `vw_average_order_value` | non-canceled |
| 6 | MoM growth | `(sales_t - sales_t-1) / sales_t-1 * 100` | `vw_mom_growth` | non-canceled |
| 7 | Payment distribution | `SUM(payment_value)` by `payment_type` | `vw_payment_distribution` | none |
| 8 | Avg delivery time | `AVG(delivery_days)` | `vw_avg_delivery_time` | delivered + non-null days |
| 9 | Late delivery % | late / delivered with estimate × 100 | `vw_late_delivery_pct` | delivered |
| 10 | Repeat purchase | customers with `order_count > 1` | `vw_customer_repeat_behaviour` | non-canceled |
| 11 | Seller performance | `SUM(price)`, avg review, ranks | `vw_seller_performance` | non-canceled |
| 12 | Review distribution | count/% by `review_score` | `vw_review_score_distribution` | all reviews |

### Delivery definitions

- **delivery_days** = `(order_delivered_customer_date - order_purchase_timestamp)` in days.
- **late delivery** = `order_delivered_customer_date > order_estimated_delivery_date` (delivered orders only).

### Repeat customer

- Segmented on **distinct non-canceled orders** per `customer_unique_id`.
- `dim_customers.is_repeat_customer` mirrors this after mart load.
