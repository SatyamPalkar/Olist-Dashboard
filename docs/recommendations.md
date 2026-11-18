# Business recommendations

**Status:** Implemented as analysis-backed recommendations from offline CSV KPIs (`docs/business_insights.md`, `scripts/ba_analysis.py`).  
**Not Verified** against a live `analytics` warehouse or controlled experiments.  
**Currency:** BRL merchandise GMV — **not** profit.

---

## Priority actions

### 1. Treat late delivery as a CX OKR

Late deliveries associate with much lower review scores (≈2.57★ late vs ≈4.29★ on-time in the offline analysis; overall late rate ≈8.11%).  

**Action:** Set a measurable late-rate reduction target by state/region; instrument seller ship-limit adherence and carrier handoff times.  
**Caveat:** Correlation ≠ causation — validate with controlled operational changes before external causal claims.

### 2. Defend Southeast share; expand carefully

SP + RJ + MG ≈ 63% of merchandise revenue.  

**Action:** Protect service levels in Southeast; expand North/Northeast only with logistics SLAs sized to observed delay risk.

### 3. Prioritise top GMV categories

Top categories (health_beauty, watches_gifts, bed_bath_table, sports_leisure, computers_accessories) drive a large share of merchandise revenue.  

**Action:** Align seller recruitment, catalogue visibility, and SLA monitoring with these lines.

### 4. Retention over pure acquisition flywheel assumptions

Repeat customer rate ≈ 3%; ≈1.03 orders per customer. Growth historically leans on new buyers.  

**Action:** Run retention tests (post-delivery offers, category cross-sell) aimed at first-order buyers; measure incrementality, avoid blanket discounting.

### 5. Protect Top-quartile spenders

Top spend quartile ≈ 62.5% of merchandise revenue despite equal headcount by construction.  

**Action:** VIP support and delivery-promise accuracy for high-spend segments; recruit assortment that supports higher AOV baskets.

### 6. Deep-dive declining / freight-heavy categories

`computers` and `cool_stuff` show clear period-over-period revenue declines in the BA windows; several low-demand categories also show high freight-to-merchandise ratios.  

**Action:** Category reviews combining revenue trend, active sellers/SKUs, and freight policy — do not cut on GMV alone without margin/availability context (margin unavailable in source data).

### 7. Assortment rationalisation for the long tail

Bottom-decile categories contribute negligible GMV and sometimes high freight ratios.  

**Action:** Rationalise where low revenue coincides with poor economics proxies; keep strategic niches explicitly.

---

## What not to recommend from this data alone

- Profit optimisation or commission changes (no COGS / fee fields).  
- Causal marketing attribution (Marketing Funnel excluded).  
- Guaranteed uplift from any single lever without testing.

---

## Traceability

| Recommendation theme | Evidence doc |
|----------------------|--------------|
| Delivery vs reviews | `business_insights.md` § Operations / cross-cutting |
| Geography concentration | § Sales A3 |
| Category leaders / decliners | § Sales A1–A2, Product D* |
| Repeat / value segments | § Customer B* |
| Formal KPI maths | `kpi_definitions.md` |
