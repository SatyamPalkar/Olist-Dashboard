# Coordination memo — BI Developer → SQL Architect

**Date:** 2026-11-18  
**From:** Agent 3 (BI Developer)  
**To:** SQL Architect  
**Re:** Analytics contract for Power BI (Import mode)

---

## What BI is consuming

Power BI will connect **only** to schema **`analytics`**, using tables defined in `database/schemas/03_analytics_tables.sql`:

- `dim_date`, `dim_geography`, `dim_customers`, `dim_products`, `dim_sellers`
- `fact_orders`, `fact_order_items`, `fact_payments`, `fact_order_reviews`

BI will **not** independently alter these SQL definitions.

---

## Schema naming conflict (needs Orchestrator ADR)

| Source | Warehouse schema name |
|--------|------------------------|
| ADR-003 / `docs/architecture.md` | `dw` |
| SQL Architect DDL + `database/README.md` | `analytics` (+ `raw`) |

**BI interim decision:** follow implemented DDL (`analytics`). Please confirm via ADR so Orchestrator docs and grants align.

---

## Assumptions baked into DAX (please confirm)

1. **Total Revenue** = `fact_orders.merchandise_sales` (canonical Revenue per `database/docs/kpi_definitions.md`). GMV is exposed separately as **Total Order Value**.
2. MoM / YoY growth use merchandise sales (matches `vw_mom_growth`).
3. AOV = `AVERAGE(order_value)` on non-canceled orders (matches `vw_average_order_value`).
4. Sales filter = `is_canceled = FALSE` (Architect). BA delivered-only remains Phase 7 — flag if you want BI to switch early.
5. `fact_orders.is_late_delivery` is NULL when delivery or estimate missing — delivery rates exclude NULLs.
6. `dim_customers.is_repeat_customer` / `order_count` match `customer_unique_id` order history.
7. **Average Review Score** prefers `fact_order_reviews` grain.
8. Unmapped categories: BI Power Query maps null English names to `Unmapped`; Architect views use `unknown` — please confirm preferred label for slicer parity.

---

## Optional asks (views — SQL Architect owned)

Nice-to-have reporting views (BI can work off base tables if these slip):

| View | Purpose |
|------|---------|
| `analytics.vw_kpi_order_daily` | Pre-aggregated daily order KPIs for smoke tests |
| `analytics.vw_category_revenue` | Category rollup for validation |

If created, document in `database/views/` and grant `SELECT` to the BI role. BI will switch Power Query to views only after you publish them — we will not invent view SQL in the warehouse folder.

---

## Validation handshake

BI ships `powerbi/validation/validate_measures.sql` mirroring each DAX measure. After analytics is loaded, run that script and paste results into the validation checklist. Flag any >0.5% discrepancy before dashboard sign-off.
