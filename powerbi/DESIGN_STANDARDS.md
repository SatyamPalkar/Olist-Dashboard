# Design standards — corporate retail analytics

## Visual language

| Token | Value | Usage |
|-------|-------|-------|
| Primary | `#0B3A53` | Headers, primary KPI values |
| Accent | `#1F7A6C` | Positive / on-time / growth |
| Alert | `#B33A3A` | Late delivery / negative growth |
| Neutral | `#5C6B73` | Secondary labels |
| Canvas | `#F5F7F8` | Page background |
| Card fill | `#FFFFFF` | KPI tiles only (interaction containers) |
| Gridline | `#D9E1E6` | Axis / separators |
| Font (titles) | Segoe UI Semibold | Page & section titles |
| Font (body) | Segoe UI | Labels, tooltips |
| Currency | `R$ #,##0` / `R$ #,##0.0,, "M"` for millions | All money |
| Percent | `0.0%` | Rates & growth |
| Decimals | `0.00` days; `0.00` review score | Delivery / reviews |

Theme file: `theme/olist_corporate.json` — import via **View → Themes → Browse**.

## Layout rules

1. **Consistent margins:** 16 px page margin; 12 px gap between visuals.
2. **KPI row:** top of page, equal-width cards, value → label → optional Δ vs prior period.
3. **One job per section:** do not mix logistics and payments on the same canvas region.
4. **Avoid chart junk:** no 3D, no dual axis unless units match, no truncated Y-axis that exaggerates change (start at 0 for absolutes; rate charts may use suitable domain with note).
5. **Accessible contrast:** text on canvas ≥ WCAG AA against background; never light grey on white for primary values.
6. **Units in titles/tooltips:** e.g. “Revenue (R$)”, “Delivery time (days)”.
7. **Colour blindness:** do not rely on red/green alone — pair with icons or labels (Late / On-time).

## Interactivity standards

| Feature | Implementation |
|---------|----------------|
| Date filters | Slicer on `dim_date[year]`, `year_month`, or between `full_date` |
| Category filters | `dim_products[product_category_name_english]` |
| Geographic filters | `dim_geography[region]`, `[state]`, `[city]` |
| Cross-filtering | Default; edit interactions to **filter** (not highlight) on KPI cards → charts |
| Drill-through | Target page “Order detail” optional stretch; MVP: category → Product Performance |
| Tooltips | Report-page tooltips for Revenue trend & Late delivery |
| Dynamic titles | Measure-driven text boxes (see DAX `Selected Period Label`) |
| Reset filters | Bookmark “Clear filters” + button on every page |

## What to avoid

- Unnecessary visuals (no vanity gauges if a KPI card + trend suffices).
- Cards inside the hero/header band for non-interactive decoration.
- Misleading scales and pie charts with >5 slices (prefer bar for category rank).
