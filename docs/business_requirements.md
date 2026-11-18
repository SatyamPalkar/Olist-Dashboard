# Business Requirements — Commercial Performance Dashboard

**Role:** Senior Business Analyst  
**Organisation:** Retail e-commerce marketplace (Olist-style platform: customers, sellers, products, payments, orders, deliveries)  
**Audience:** Executive leadership, commercial, operations, and customer experience stakeholders  
**Data foundation:** Brazilian e-commerce public marketplace dataset (delivered orders, Sep 2016 – Aug 2018)

---

## 1. Purpose

Translate transactional marketplace data into a management dashboard that answers commercial, customer, operational, and product questions — and supports prioritised improvement actions.

This document defines **what** the dashboard must answer, **for whom**, and **how often**. Metric formulas are documented in `kpi_definitions.md`. Evidence-based findings are in `business_insights.md`. Recommended actions are in `recommendations.md`.

---

## 2. Stakeholders

| Stakeholder | Primary interest | Decision supported |
|---|---|---|
| CEO / Executive Committee | Overall commercial health, growth, risk | Prioritise investment and strategic focus |
| Commercial / Category Management | Category sales, contribution, decline/growth | Assortment, promotions, seller recruitment |
| Marketing / CRM | Customer frequency, repeat rate, value segments | Retention programmes and acquisition ROI |
| Operations / Logistics | Delivery time, late rate, regional delays | Carrier SLAs, promise dating, capacity |
| Customer Experience | Review scores linked to delivery | CX programmes and complaint reduction |
| Finance / FP&A | Revenue, freight, AOV, monthly trends | Forecasting and commercial planning |
| Data / BI | KPI definitions, dimensions, refresh | Dashboard build and data quality |

---

## 3. Key business objectives

1. **Understand commercial performance** — merchandise sales, freight, order value, and growth trajectory.
2. **Identify where revenue concentrates** — categories and customer regions that drive (or dilute) GMV.
3. **Improve retention economics** — measure repeat purchasing and high-value segments.
4. **Reduce delivery-related CX risk** — quantify lateness, regional hotspots, and association with reviews.
5. **Prioritise category actions** — grow leaders, investigate decliners, and review freight-heavy low-demand lines.

---

## 4. Business questions the dashboard must answer

### 4.1 Sales

- Which categories generate the highest sales?
- Which categories are declining?
- What are the monthly revenue trends?
- Which regions generate the most revenue?

### 4.2 Customers

- How frequently do customers purchase?
- What proportion of customers place repeat orders?
- Which customer segments are most valuable?

### 4.3 Operations

- How often are orders delivered late?
- Which regions experience delivery delays?
- Is delivery performance associated with review scores?

### 4.4 Products

- Which categories have the highest sales?
- Which categories have low demand?
- How do freight charges vary by category?

---

## 5. Reporting requirements

### 5.1 Dashboard views (minimum viable)

| View | Content | Primary users |
|---|---|---|
| Executive overview | Headline KPIs, MoM growth, late %, repeat rate | Executives |
| Sales & category | Category revenue, share, growth/decline, freight ratio | Commercial |
| Geography | Revenue and late % by customer state | Commercial + Ops |
| Customers | Unique customers, repeat rate, orders/customer, value quartiles | Marketing / CRM |
| Operations | Avg delivery days, late %, estimated vs actual, review by late/on-time | Ops / CX |
| Trends | Monthly merchandise revenue and order volume | FP&A / Executives |

### 5.2 Filters / slice capability

- Time period (month, quarter, year; purchase date)
- Order status (default: **delivered** for commercial KPIs)
- Customer state / region
- Product category (English translation preferred)
- Optional: payment type, seller state (phase 2)

### 5.3 Presentation standards

- Separate **merchandise revenue** from **freight** and from **profit** (profit is out of scope without cost data).
- Label observations vs recommendations clearly.
- Show period coverage and row filters on every view.
- Do not present incomplete early months (e.g. sparse 2016) as normal run-rate without caveat.

---

## 6. Required KPIs

### Commercial

- Merchandise revenue  
- Freight charges  
- Total order value  
- Average order value (AOV)  
- Monthly revenue growth (MoM %)

### Customer

- Unique customers  
- Repeat customer rate  
- Orders per customer  
- Average review score  

### Operational

- Average delivery time (days)  
- Late delivery percentage  
- Estimated versus actual delivery time  

### Product

- Revenue by category  
- Product order volume (items / orders)  
- Category contribution (% of merchandise revenue)  

Full definitions, grain, and SQL logic: `kpi_definitions.md`.

---

## 7. Relevant dimensions

| Dimension | Source field(s) | Use |
|---|---|---|
| Time | `orders.order_purchase_timestamp` | Monthly trends, MoM growth |
| Order status | `orders.order_status` | Filter commercial base to delivered |
| Customer | `customers.customer_unique_id` | Unique customers, repeat behaviour |
| Geography | `customers.customer_state`, `customer_city` | Regional revenue and lateness |
| Category | `products.product_category_name` + English translation | Category performance |
| Product | `products.product_id` | Volume and assortment |
| Seller | `sellers.seller_id`, `seller_state` | Phase 2 fulfilment analysis |
| Delivery dates | purchase / estimated / actual delivery timestamps | Ops KPIs |
| Review | `order_reviews.review_score` | CX association with delivery |

---

## 8. Reporting frequency

| Cadence | Content | Audience |
|---|---|---|
| **Daily** (operational) | Late deliveries in last 7–30 days; open delivery exceptions | Operations |
| **Weekly** | Trailing 7/28-day revenue, AOV, late %, review score | Commercial + Ops |
| **Monthly** | Full KPI pack, category contribution, regional scorecard, MoM growth | Executives + all stakeholders |
| **Quarterly** | Strategic review: retention, category portfolio, regional logistics | Executive Committee |

**Initial dashboard refresh assumption:** batch daily from warehouse tables derived from transactional extracts; monthly pack is the primary management rhythm.

---

## 9. Scope, assumptions, and exclusions

### In scope

- Delivered-order commercial performance (merchandise + freight from order items).
- Customer repeat and value segmentation from observed orders.
- Delivery punctuality vs estimated date and association with review scores.
- Category and state-level analysis.

### Out of scope (unless cost data is added later)

- **Profit, margin, or contribution margin** (no COGS, marketplace take-rate, or fulfilment cost ledger in source).
- Causal claims (e.g. “lateness causes low reviews”) — only association is measurable.
- Real-time streaming operational control tower (phase 2).

### Assumptions

- `price` on order items = merchandise value charged for the item.  
- `freight_value` = freight charged on the item line.  
- `customer_unique_id` identifies a person/household for repeat analysis.  
- An order is **late** when `order_delivered_customer_date` > `order_estimated_delivery_date`.  
- English category names are preferred for management reporting via the translation table.

### Data quality notes for requirements

- Sparse early months (2016) distort MoM growth — dashboard must flag low-volume periods.  
- Some products lack category translation — report as `unknown` or Portuguese fallback.  
- Multiple reviews per order: use order-level average score for CX KPIs.

---

## 10. Acceptance criteria (definition of done for requirements)

- [ ] Every dashboard KPI maps to a named definition in `kpi_definitions.md`.
- [ ] Every business question in §4 has a supporting view or chart.
- [ ] Stakeholders in §2 can answer their primary questions without reading SQL.
- [ ] Revenue is never labelled as profit.
- [ ] Limitations and filters are visible on the dashboard or in accompanying insight packs.
- [ ] Recommendations are traceable to analysis in `business_insights.md` / `recommendations.md`.

---

## 11. Related documents

| Document | Purpose |
|---|---|
| `kpi_definitions.md` | Metric dictionary and SQL calculations |
| `business_insights.md` | Evidence-based answers to business questions |
| `recommendations.md` | Management actions and executive summary |
