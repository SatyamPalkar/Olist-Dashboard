# Page 2 — Sales Performance

**Primary facts:** `fact_orders`, `fact_order_items`, `fact_payments`

## KPI strip

| Measure | Purpose |
|---------|---------|
| `[Total Revenue]` | Headline |
| `[Revenue MoM Growth]` | Momentum |
| `[Revenue YoY Growth]` | YoY where prior year exists (blank if no prior) |
| `[Average Order Value]` | Basket size |

## Visuals

| # | Visual | Spec |
|---|--------|------|
| 1 | Clustered column — Monthly revenue | Axis: `year_month` · `[Total Revenue]` |
| 2 | Clustered column — Quarterly comparisons | Axis: `year` + `quarter` · `[Total Revenue]` |
| 3 | Card + line — Revenue growth | `[Revenue MoM Growth]` trend by month |
| 4 | Treemap or bar — Category performance | Category EN · `[Merchandise Revenue (Items)]` |
| 5 | Table — Product rankings | `product_id` (or key) · Revenue, Units (`COUNTROWS` items), Avg price · Top 20 by revenue |
| 6 | Bar — Seller performance | `dim_sellers[seller_id]` Top 15 · `[Merchandise Revenue (Items)]` |
| 7 | Donut / bar — Payment method distribution | Legend: `fact_payments[payment_type]` · `[Payment Value]` · Prefer bar if >5 types |

## Notes

- YoY will be blank/thin for early 2017 months without 2016 overlap — show “n/a” via measure IF if desired.
- Do not place payment value and item revenue on one stacked visual without labeling different grains.
