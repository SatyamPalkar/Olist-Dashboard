# Build guide — assemble the report in Power BI Desktop

This is the path to Definition of Done. Artefacts in this folder are inputs; the `.pbix` is the output created **on the operator machine**.

## Prerequisites checklist

- [ ] PostgreSQL running with `analytics` populated
- [ ] Power BI Desktop installed
- [ ] `.env` credentials work via `psql` / DBeaver
- [ ] `validation/validate_measures.sql` returns rows (baseline numbers recorded)

## Assembly steps

1. **New report** → save as `powerbi/Olist_Retail_Analytics.pbix` (gitignored if binary policy requires; keep path documented).
2. **Theme:** View → Themes → Browse → `theme/olist_corporate.json`.
3. **Connect** per `CONNECTION.md` (Import) using M from `powerquery/`.
4. **Model:** create relationships exactly as `SEMANTIC_MODEL.md`.
5. **Mark date table:** `dim_date[full_date]`.
6. **Measures table:** Enter Data → empty table named `_Measures` → paste measures from `dax/measures.dax` (New measure repeatedly, or use external tools / TMDL if available).
7. **Pages:** create five pages matching `pages/01` … `pages/05` specs (names, visuals, fields).
8. **Slicers:** sync Year / Category / Region / State across pages (Sync slicers pane).
9. **Bookmarks:** “Default view” + “Reset filters”; assign Reset button on each page.
10. **Tooltips:** optional report pages `Tip Revenue`, `Tip Delivery`.
11. **Refresh** once; compare KPI cards to SQL validation sheet (±0.5%).
12. **Screenshots:** export each page PNG into `screenshots/` with names listed in `screenshots/README.md`.
13. **Publish (optional):** Power BI Service + gateway for scheduled refresh.

## File naming convention for screenshots

```
screenshots/01_executive_overview.png
screenshots/02_sales_performance.png
screenshots/03_customer_analytics.png
screenshots/04_logistics_delivery.png
screenshots/05_product_performance.png
```
