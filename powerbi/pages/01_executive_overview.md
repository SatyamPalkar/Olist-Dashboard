# Page 1 — Executive Overview

**Audience:** Management  
**Primary fact:** `fact_orders` (+ items for category)  
**Dynamic title:** `[Page Title Executive]`

## Global slicers (synced)

| Slicer | Field |
|--------|-------|
| Year | `dim_date[year]` |
| Month | `dim_date[year_month]` |
| Region | `dim_geography[region]` |
| State | `dim_geography[state]` |
| Category | `dim_products[product_category_name_english]` |

Reset filters button → bookmark **Reset filters**.

## KPI cards (top row)

| Card | Measure | Format | Tooltip |
|------|---------|--------|---------|
| Total revenue | `[Total Revenue]` | R$ | MoM: `[Revenue MoM Growth]` |
| Total orders | `[Total Orders]` | #,##0 | vs prior month orders |
| Average order value | `[Average Order Value]` | R$ | Revenue ÷ orders |
| Unique customers | `[Unique Customers]` | #,##0 | Distinct customers in filter |
| Average review score | `[Average Review Score]` | 0.00 | From review fact |
| On-time delivery rate | `[On-time Delivery Rate]` | 0.0% | Delivered with SLA dates |

## Visuals

| # | Visual | Values / axis | Notes |
|---|--------|---------------|-------|
| 1 | Line chart — Revenue trend | Axis: `dim_date[year_month]` · Values: `[Total Revenue]` | Y starts at 0; tooltip page optional |
| 2 | Line/column — Orders over time | Axis: `year_month` · Values: `[Total Orders]` | |
| 3 | Horizontal bar — Revenue by category | Axis: category EN · Values: `[Merchandise Revenue (Items)]` | Top 10; rest in “Other” via filter or Top N |
| 4 | Map or bar — Regional sales | Location: `state` / `region` · Values: `[Total Revenue]` | Prefer bar if map basemap unavailable |
| 5 | Bar — Top-performing categories | Same as #3 sorted desc · Top 5 | |

## Interactions

- KPI cards do not cross-filter charts (edit interactions → None).
- Charts cross-filter each other.
- Category slicer filters item-based charts; order KPIs filter via shared date/customer/geo.
