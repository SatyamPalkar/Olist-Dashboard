# Validation checklist — Power BI vs PostgreSQL

**Rule:** Do not sign off the dashboard until every required measure matches SQL within tolerance.

**Tolerance:** counts exact; currency/rates within **0.5%** relative error (floating rounding).

## A. Environment

| # | Check | Pass? | Evidence |
|---|-------|-------|----------|
| A1 | Postgres reachable; `analytics` tables non-empty | ☐ | row counts |
| A2 | Import mode (not DirectQuery) on all queries | ☐ | Model view |
| A3 | Relationships match `SEMANTIC_MODEL.md` | ☐ | |
| A4 | `dim_date` marked as date table on `full_date` | ☐ | |
| A5 | Theme applied | ☐ | |

## B. Measure parity (blank filter context)

| # | Measure | SQL section | DAX value | SQL value | Pass? |
|---|---------|-------------|-----------|-----------|-------|
| B1 | Total Revenue (= merchandise) | §1 | | | ☐ |
| B2 | Merchandise Revenue | §2 | | | ☐ |
| B3 | Freight Revenue | §3 | | | ☐ |
| B3b | Total Order Value (GMV) | §3b | | | ☐ |
| B4 | Total Orders | §4 | | | ☐ |
| B5 | Average Order Value | §5 | | | ☐ |
| B6 | Unique Customers | §6 | | | ☐ |
| B7 | Repeat Customer Rate | §7 | | | ☐ |
| B8 | Revenue MoM Growth | §8 (same month) | | | ☐ |
| B9 | Revenue YoY Growth | §9 (month with prior year) | | | ☐ |
| B10 | Average Delivery Time | §10 | | | ☐ |
| B11 | Late Delivery Rate | §11 | | | ☐ |
| B12 | On-time Delivery Rate | §12 | | | ☐ |
| B13 | Average Review Score | §13 review fact | | | ☐ |

## C. Page interactivity

| # | Check | Pass? |
|---|-------|-------|
| C1 | Date / category / geo slicers sync across 5 pages | ☐ |
| C2 | Cross-filtering works; KPI cards do not blank peers oddly | ☐ |
| C3 | Reset filters bookmark restores default | ☐ |
| C4 | Dynamic title updates with slicers | ☐ |
| C5 | Tooltips show units (R$, days, %) | ☐ |
| C6 | Drill-through to Product Performance (if configured) | ☐ |

## D. Deliverables honesty

| # | Check | Pass? |
|---|-------|-------|
| D1 | `.pbix` exists and opens against Postgres | ☐ **blocked until Desktop build** |
| D2 | Screenshots for pages 01–05 captured | ☐ **blocked until Desktop build** |
| D3 | No CSV used as final dashboard source | ☐ |

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| BI Developer | | | |
| SQL Architect (parity) | | | |
| QA Engineer | | | |
| Orchestrator | | | |
