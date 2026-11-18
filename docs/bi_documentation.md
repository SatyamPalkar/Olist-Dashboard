# BI documentation (Power BI)

**Status:** Design artefacts **Implemented**; interactive `.pbix` and screenshots **Planned** (not built / not Verified).  
**Package root:** [`../powerbi/`](../powerbi/)  
**Mode:** Import against PostgreSQL schema `analytics` (ADR-004)

---

## PostgreSQL connection

| Setting | Value |
|---------|-------|
| Connector | PostgreSQL database |
| Database | `POSTGRES_DB` (default `olist_bi`) |
| Schema | `analytics` only |
| Mode | **Import** (not DirectQuery for MVP) |
| Credentials | From `.env` / Desktop credential store — never in Git |

Steps, grants, parameters, and refresh notes: [`../powerbi/CONNECTION.md`](../powerbi/CONNECTION.md).

**Do not** bind the dashboard to `raw.*`, `staging.*`, or static CSV exports for the final report.

---

## Data model

Star schema imported from analytics:

| Table | Role |
|-------|------|
| `dim_date` | Date spine |
| `dim_geography` | Zip / state / region |
| `dim_customers` | Unique customers |
| `dim_products` | Products + EN category |
| `dim_sellers` | Sellers |
| `fact_orders` | Order-grain KPIs |
| `fact_order_items` | Line-grain revenue by product/seller |
| `fact_payments` | Payment mix |
| `fact_order_reviews` | Review scores |

Relationships (many→one facts to dims on surrogate keys): [`../powerbi/SEMANTIC_MODEL.md`](../powerbi/SEMANTIC_MODEL.md) and [`../database/docs/er_diagram.md`](../database/docs/er_diagram.md).

Power Query M scripts: [`../powerbi/powerquery/`](../powerbi/powerquery/).

---

## DAX measures

Source file: [`../powerbi/dax/measures.dax`](../powerbi/dax/measures.dax)  
Home table in Desktop: create empty `_Measures`, paste measures.

| Measure (examples) | Logic (summary) |
|--------------------|-----------------|
| `Total Revenue` / `Merchandise Revenue` | `SUM(fact_orders[merchandise_sales])` with sales filter |
| `Freight Revenue` | Sum freight charges |
| `Total Order Value` | merchandise + freight (`order_value`) — **not profit** |
| `Total Orders` | Distinct `order_id` |
| `Average Order Value` | Average `order_value` |
| `Unique Customers` | Distinct customer keys |
| `Repeat Customer Rate` | Repeat / unique |
| `Average Review Score` | From review fact |
| `On-time` / `Late Delivery Rate` | Using `is_late_delivery` on delivered rows |
| MoM / YoY revenue | Time intelligence on merchandise revenue |

### Filter policy (important)

- **Current DAX default:** `fact_orders[is_canceled] = FALSE` (SQL Architect alignment).
- **BA KPI dictionary preference:** `order_status = 'delivered'` only.
- **Status:** Pending Phase 7 sign-off — do not silently change warehouse SQL from BI. Document which filter a visual uses.

SQL parity queries: [`../powerbi/validation/validate_measures.sql`](../powerbi/validation/validate_measures.sql).

---

## Dashboard pages

| # | Page | Spec | Status |
|---|------|------|--------|
| 1 | Executive Overview | `powerbi/pages/01_executive_overview.md` | Spec Implemented |
| 2 | Sales Performance | `powerbi/pages/02_sales_performance.md` | Spec Implemented |
| 3 | Customer Analytics | `powerbi/pages/03_customer_analytics.md` | Spec Implemented |
| 4 | Logistics & Delivery | `powerbi/pages/04_logistics_delivery.md` | Spec Implemented |
| 5 | Product Performance | `powerbi/pages/05_product_performance.md` | Spec Implemented |

Interactive report binary: **Planned**.

---

## Filters

Global slicers (synced across pages per page specs):

- Year / Month (`dim_date`)
- Region / State (`dim_geography`)
- Category (`dim_products[product_category_name_english]`)

Reset via bookmark **Reset filters** (specified; not Verified in a live PBIX).

Visual interaction rules (example Executive page): KPI cards do not cross-filter charts; charts cross-filter each other.

---

## Drill-through

Page specifications describe tooltip/drill behaviours where relevant. **Live drill-through pages are Planned** with the Desktop build — not Verified.

Guidance: keep drill targets on order or product details using keys already in the star schema; do not invent attributes.

---

## Refresh strategy

| Environment | Approach | Status |
|-------------|----------|--------|
| Local Desktop | Home → Refresh after ETL completes | Documented |
| Power BI Service + gateway | Scheduled refresh to private Postgres | Planned |
| Incremental refresh | Optional stretch | Out of MVP scope |

**Order of operations:** finish `raw` → `staging` → `analytics` (and MV refresh) **before** Power BI refresh. Credentials rotate with `.env`, not source control.

---

## Screenshots

**None yet.** Placeholder policy: [`../powerbi/screenshots/README.md`](../powerbi/screenshots/README.md).

---

## Build path

1. Warehouse populated and smoke SQL OK.  
2. Follow [`../powerbi/BUILD_GUIDE.md`](../powerbi/BUILD_GUIDE.md).  
3. Apply theme [`../powerbi/theme/olist_corporate.json`](../powerbi/theme/olist_corporate.json).  
4. Tick [`../powerbi/validation/checklist.md`](../powerbi/validation/checklist.md).  
5. Capture screenshots; update [`progress.md`](progress.md) to Verified only with evidence.
