# Page 3 — Customer Analytics

**Primary facts:** `fact_orders`, `fact_order_reviews`  
**Primary dims:** `dim_customers`, `dim_geography`

## KPI strip

| Measure |
|---------|
| `[Unique Customers]` |
| `[Repeat Customer Rate]` |
| `[Customer Order Frequency]` |
| `[Average Review Score]` |

## Visuals

| # | Visual | Spec |
|---|--------|------|
| 1 | Card cluster | Unique customers + repeat rate |
| 2 | Histogram / column — Customer order frequency | Axis: `dim_customers[order_count]` (or grouped buckets) · Distinct customers |
| 3 | Map or bar — Customer geographic distribution | `state` / `region` · `[Unique Customers]` or `[Total Orders]` |
| 4 | Column — Customer review scores | Axis: `fact_order_reviews[review_score]` (1–5) · `[Review Count]` |
| 5 | Scatter / column — Purchase behaviour | Avg `[Average Order Value]` by `order_count` band or state |
| 6 | Table — Repeat vs one-time | `is_repeat_customer` · Customers, Orders, Revenue |

## Behaviour notes

- Repeat rate uses `dim_customers.is_repeat_customer` (SQL Architect SCD attributes).
- Frequency visual should use customer dimension grain to avoid order double-counting.
