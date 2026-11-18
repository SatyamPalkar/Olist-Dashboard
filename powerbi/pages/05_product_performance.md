# Page 5 — Product Performance

**Primary fact:** `fact_order_items`  
**Primary dim:** `dim_products`

## KPI strip

| Measure |
|---------|
| `[Merchandise Revenue (Items)]` |
| `[Freight Revenue (Items)]` |
| `[Total Order Value (Items)]` |
| Item count = `COUNTROWS ( fact_order_items )` (add measure if desired) |

## Visuals

| # | Visual | Spec |
|---|--------|------|
| 1 | Bar — Category revenue | Category EN · `[Merchandise Revenue (Items)]` |
| 2 | Bar — Category order volume | Category EN · distinct `order_id` or `COUNTROWS` |
| 3 | Dual tables — Top and bottom products | Top 10 / Bottom 10 by merchandise revenue · columns: product_id, category, revenue, freight, lines |
| 4 | Histogram — Product price distribution | Axis: price buckets (group `fact_order_items[price]` in PQ or visual binning) · line count |
| 5 | Bar — Freight charges by category | Category EN · `[Freight Revenue (Items)]` |

## Drill-through

- From Executive / Sales category bar → this page (drill-through filter on category).
- Keep Year / Region slicers synced.

## Notes

- Rankings use item grain — correct for product/seller analysis.
- Bottom products: filter out tiny sample sizes (e.g. ≥10 lines) via visual filter to avoid noise.
