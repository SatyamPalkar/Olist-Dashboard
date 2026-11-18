# Business requirements & KPI candidates

**Owner:** Business Analyst (drafted by Orchestrator for Phase 1)  
**Constraint:** Every metric must map to documented Olist columns. No invented fields.

---

## 1. Stakeholders (persona)

| Persona | Primary need |
|---------|----------------|
| Marketplace ops lead | Order volume, status mix, delivery SLA |
| Commercial / category lead | Revenue by category & seller |
| Customer experience | Review scores, late deliveries vs dissatisfaction |
| Finance / payments | Payment mix, installment behaviour |

---

## 2. Core business questions

1. How many orders were placed over time, and what is the status mix?
2. What is GMV (item price sum) and freight contribution over time?
3. Which product categories (English names) drive the most revenue?
4. Which customer states / cities concentrate demand?
5. How do sellers perform on revenue and average review score?
6. What share of deliveries are early / on-time / late vs estimated date?
7. What is the payment method mix and typical installment depth?
8. What is the repeat-purchase rate using `customer_unique_id`?

---

## 3. KPI candidates (field-backed)

| KPI | Definition (draft) | Source columns | Filter notes |
|-----|--------------------|----------------|--------------|
| Order count | Count distinct `order_id` | `orders.order_id` | Optionally exclude `canceled` / `unavailable` — confirm in Phase 7 |
| GMV (item) | Sum of `price` | `order_items.price` | Align with delivered / approved policy in Phase 7 |
| Freight revenue | Sum of `freight_value` | `order_items.freight_value` | Same filter policy as GMV |
| AOV (order) | GMV / order count | Derived | Same grain/filter |
| Avg review score | Avg `review_score` | `order_reviews.review_score` | Grain after dedupe ADR |
| On-time delivery rate | Share where `order_delivered_customer_date` ≤ `order_estimated_delivery_date` | orders timestamps | Only rows with both dates present |
| Late delivery rate | Complement of on-time among delivered with dates | orders timestamps | Same |
| Delivery lead time (days) | Diff purchase → delivered customer | `order_purchase_timestamp`, `order_delivered_customer_date` | Delivered only |
| Payment mix | % of `payment_value` by `payment_type` | payments | — |
| Avg installments | Avg `payment_installments` | payments | Exclude or flag `not_defined` in Phase 7 |
| Repeat customer rate | Share of `customer_unique_id` with >1 order | customers + orders | Via `customer_unique_id` |
| Category revenue | Sum `price` by English category | items + products + translation | Unmapped categories labelled explicitly |

**Naming note:** Source columns `product_name_lenght` / `product_description_lenght` retain Olist spelling; they are not KPIs for MVP.

---

## 4. Non-functional requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Clone → configure `.env` → `docker compose up` → load data → query `dw` |
| NFR-2 | Raw CSVs never modified in place |
| NFR-3 | Automated tests for PK uniqueness, orphan FKs, and KPI smoke checks |
| NFR-4 | No secrets in Git |
| NFR-5 | Docs sufficient for a technical interviewer to follow the pipeline |

---

## 5. MVP dashboard scope (Phase 8 preview)

1. **Executive overview** — orders, GMV, AOV, avg review, on-time rate  
2. **Sales & category** — time series + category breakdown  
3. **Geography** — state-level demand  
4. **Logistics** — delivery performance  
5. **Payments** — method mix  

Detailed wireframes deferred to BI Developer after KPI sign-off (Phase 7).

---

## 6. Acceptance criteria (Phase 1)

- [x] Questions and KPIs reference only inventoried columns
- [x] Out-of-scope items called out (Marketing Funnel, invented metrics)
- [ ] Operator has downloaded CSVs into `data/raw/` (human action)
- [ ] BA confirms KPI filter policy in Phase 7 (delivered-only vs all statuses)
