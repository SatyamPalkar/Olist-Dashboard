# Power BI — Olist Retail Analytics Dashboard

**Owner:** Agent 3 (BI Developer)  
**Status:** Specs + semantic artefacts ready · **`.pbix` not built yet**  
**Data source:** PostgreSQL schema `analytics` (SQL Architect star schema)  
**Currency:** BRL (R$)

---

## Honest delivery status

| Deliverable | Status |
|-------------|--------|
| Dashboard page specifications (5 pages) | Ready — `pages/` |
| DAX measures (dedicated `_Measures` table) | Ready — `dax/measures.dax` |
| Power Query (M) for all dims/facts | Ready — `powerquery/` |
| PostgreSQL connection + refresh docs | Ready — `CONNECTION.md` |
| Import vs DirectQuery recommendation | Ready — `CONNECTION.md` |
| Semantic model / relationships | Ready — `SEMANTIC_MODEL.md` |
| SQL validation queries for every measure | Ready — `validation/validate_measures.sql` |
| Validation checklist | Ready — `validation/checklist.md` |
| Design standards + theme tokens | Ready — `DESIGN_STANDARDS.md` |
| Dashboard screenshots | **Blocked** — requires Power BI Desktop + live Postgres load |
| Functioning interactive `.pbix` | **Not created** — must be built in Power BI Desktop (see build guide) |

> Per project rules: this package does **not** fabricate a PBIX binary or claim a live report exists.

---

## Build prerequisites (Definition of Done path)

1. SQL Architect completes `analytics` dims/facts + population scripts.
2. Data Engineer loads Olist CSVs → `raw` → staging → analytics.
3. Operator confirms KPI smoke queries in `validation/validate_measures.sql`.
4. Install **Power BI Desktop** (Windows).
5. Follow `CONNECTION.md` + `BUILD_GUIDE.md` to assemble the report from these artefacts.
6. Capture screenshots into `screenshots/` and tick `validation/checklist.md`.

---

## Package layout

```
powerbi/
├── README.md
├── BUILD_GUIDE.md              # Step-by-step Desktop assembly
├── CONNECTION.md               # Postgres connect, Import vs DQ, refresh
├── SEMANTIC_MODEL.md           # Star schema relationships in PBI
├── DESIGN_STANDARDS.md         # Visual language, accessibility
├── COORDINATION_SQL_ARCHITECT.md
├── pages/                      # Five page specs
├── dax/measures.dax            # Paste into Desktop
├── powerquery/                 # M scripts per table
├── validation/                 # SQL parity checks + checklist
├── theme/olist_corporate.json  # Report theme
└── screenshots/                # Empty until Desktop build
```

---

## KPI source-of-truth mapping

Aligned to `docs/requirements.md` and `database/schemas/03_analytics_tables.sql`:

| Dashboard KPI | Canonical fact column / rule |
|---------------|------------------------------|
| Total Revenue | `fact_orders.merchandise_sales` (= SUM price; SQL Architect “Revenue”) |
| Merchandise Revenue | Alias of Total Revenue |
| Freight Revenue | `fact_orders.freight_charges` / `fact_order_items.freight_value` |
| Total Order Value (GMV) | `fact_orders.order_value` (merchandise + freight) — not labelled profit |
| Total Orders | Count of `fact_orders.order_id` |
| Average Order Value | `AVERAGE(fact_orders[order_value])` non-canceled |
| Unique Customers | Distinct customer keys on non-canceled orders |
| Repeat Customer Rate | Customers with >1 order ÷ unique customers |
| Average Review Score | Avg `fact_order_reviews.review_score` (preferred) |
| On-time Delivery Rate | Delivered with dates where `is_late_delivery = FALSE` |
| Late Delivery Rate | Delivered with dates where `is_late_delivery = TRUE` |
| Average Delivery Time | Avg `fact_orders.delivery_days` (delivered only) |
| Revenue MoM / YoY | Time intel on **merchandise** Total Revenue |

**Filter policy:** sales measures follow SQL Architect (`is_canceled = FALSE`). BA `docs/kpi_definitions.md` prefers **delivered-only** — Phase 7 sign-off may require swapping the filter; do not change warehouse SQL from BI. Delivery KPIs already restrict to delivered + known SLA flags.

---

## Coordination notes

- Connect **only** to `analytics.*` — never `raw` or `staging` (per SQL Architect `database/README.md`).
- Orchestrator ADR-003 still names warehouse schema `dw`; SQL Architect implemented `analytics`. BI follows the **implemented DDL**. See `COORDINATION_SQL_ARCHITECT.md`.
- Do not alter SQL reporting definitions from this agent; raise view needs via the coordination memo.
