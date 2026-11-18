# Page 4 — Logistics and Delivery

**Primary fact:** `fact_orders`  
**Filters:** delivered orders with SLA (`is_late_delivery` not blank)

## KPI strip

| Measure |
|---------|
| `[Average Delivery Time]` |
| `[On-time Delivery Rate]` |
| `[Late Delivery Rate]` |
| `[Average Review Score]` |

## Visuals

| # | Visual | Spec |
|---|--------|------|
| 1 | Card — Average delivery time | Days; tooltip: sample = delivered with `delivery_days` |
| 2 | Combo / scatter — Estimated versus actual | Use inactive date relationships **or** precomputed `delivery_days` + late flag; MVP: column `[Average Delivery Time]` by `year_month` + late rate line |
| 3 | Line — Late delivery rate over time | Axis: `year_month` · `[Late Delivery Rate]` |
| 4 | Bar — Delivery performance by region | Axis: `dim_geography[region]` / `state` · On-time rate + avg days |
| 5 | Scatter — Review score versus delivery performance | X: avg delivery days (state) · Y: avg review · Size: orders · Colour: late rate |

## Tooltip page (optional)

Show: order count, late %, avg days, avg review for hovered region/month.

## Caution

- Exclude canceled / non-delivered from rate denominators (measures already do).
- Do not chart `is_late_delivery` as average of boolean without converting — use the rate measures.
