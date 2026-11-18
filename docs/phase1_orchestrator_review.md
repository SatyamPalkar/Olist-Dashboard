# Phase 1 — Orchestrator gate review

**Project:** Retail Business Intelligence Platform (Olist)  
**Role:** Project Orchestrator  
**Date:** 2026-11-18  
**Status:** AWAITING YOUR APPROVAL — do not start Phase 2+ until signed off

---

## 0. Blocker: specialist agent instructions missing

Requested path: `.cursor/agents/` (seven specialist instruction files).

**Finding:** `f:\dev\satyam_project\.cursor` is an **empty file**, not a directory. There is no `.cursor/agents/` tree in the project. `~/.cursor/agents/` also exists but is empty.

**Implied specialist set** (from `docs/project_plan.md` + this engagement):

| # | Role | Phase 1 use |
|---|------|-------------|
| 0 | Project Orchestrator | This review |
| 1 | Data Engineer | Dataset profiling (delegated — done) |
| 2 | SQL Architect | Architecture proposal only (no DDL freeze yet) |
| 3 | BI Developer | Deferred |
| 4 | QA Engineer | Deferred |
| 5 | Business Analyst | Requirements / KPI candidates (draft only) |
| 6 | Documentation Engineer | Deferred |

**Decision needed:** Confirm the seven agent names/scopes and whether to create project agents under `.cursor/agents/` after converting `.cursor` from file → directory.

---

## 1. Repository inspection (as-of Phase 1 gate)

### Present and in-scope for Phase 1

| Area | Status |
|------|--------|
| `data/raw/` — 9 Olist CSVs | Present |
| `docs/dataset_inventory.md` | Present (needs count refresh — see §3) |
| `docs/requirements.md` | Present (KPI **candidates**) |
| `docs/data_profile.md` (+ JSON + profiler script) | Present — Data Engineer deliverable |
| `docs/architecture.md`, `project_plan.md`, `decisions.md`, `progress.md` | Present |
| Git | Initialized; **no commits yet**; many untracked files |

### Premature work (beyond Phase 1 — not approved by this gate)

Parallel activity already created assets that Phase 1 explicitly deferred:

- `database/schemas/*.sql`, `database/staging/*.sql`, `database/marts/*.sql`, views, seeds, DQ SQL
- `tests/` suite scaffolding
- `docs/kpi_definitions.md`, `business_insights.md`, `recommendations.md` (analysis ahead of gate)
- `powerbi/validation/`
- Schema-name conflict: `docs/architecture.md` / ADR-003 use `staging` + `dw`; `database/` uses `raw` + `staging` + `analytics`

**Orchestrator stance:** Treat all of the above as **draft / provisional**. They must not be treated as frozen contracts until you approve Phase 1 and subsequent phases. Prefer review-before-keep vs silent acceptance.

---

## 2. Dataset inventory (verified)

Ground truth: files in `data/raw/` + Data Engineer profile ([Data Engineer](35372a81-f2c9-41f5-bfcf-6210bbd59d5a) → `docs/data_profile.md`).

| File | Bytes | Rows (excl. header) | Cols | Declared grain |
|------|------:|--------------------:|-----:|----------------|
| `olist_orders_dataset.csv` | 17,654,914 | 99,441 | 8 | 1 / `order_id` |
| `olist_order_items_dataset.csv` | 15,007,623 | 112,650 | 7 | 1 / (`order_id`,`order_item_id`) |
| `olist_order_payments_dataset.csv` | 5,647,783 | 103,886 | 5 | 1 / (`order_id`,`payment_sequential`) |
| `olist_order_reviews_dataset.csv` | 14,451,670 | 99,224 | 7 | review rows linked to `order_id` (**`review_id` not unique**) |
| `olist_customers_dataset.csv` | 8,562,270 | 99,441 | 5 | 1 / `customer_id` (order-scoped) |
| `olist_products_dataset.csv` | 2,379,446 | 32,951 | 9 | 1 / `product_id` |
| `olist_sellers_dataset.csv` | 163,589 | 3,095 | 4 | 1 / `seller_id` |
| `olist_geolocation_dataset.csv` | 61,273,883 | 1,000,163 | 5 | many / zip prefix |
| `product_category_name_translation.csv` | 2,613 | 71 | 2 | 1 / `product_category_name` |

**Note:** Physical `wc -l` on reviews is higher than 99,224 because multiline quoted review text spans lines; logical CSV rows = 99,224.

### Exact columns (file order — no renames)

- **orders:** `order_id`, `customer_id`, `order_status`, `order_purchase_timestamp`, `order_approved_at`, `order_delivered_carrier_date`, `order_delivered_customer_date`, `order_estimated_delivery_date`
- **order_items:** `order_id`, `order_item_id`, `product_id`, `seller_id`, `shipping_limit_date`, `price`, `freight_value`
- **payments:** `order_id`, `payment_sequential`, `payment_type`, `payment_installments`, `payment_value`
- **reviews:** `review_id`, `order_id`, `review_score`, `review_comment_title`, `review_comment_message`, `review_creation_date`, `review_answer_timestamp`
- **customers:** `customer_id`, `customer_unique_id`, `customer_zip_code_prefix`, `customer_city`, `customer_state`
- **products:** `product_id`, `product_category_name`, `product_name_lenght`, `product_description_lenght`, `product_photos_qty`, `product_weight_g`, `product_length_cm`, `product_height_cm`, `product_width_cm` *(source spelling `lenght` retained)*
- **sellers:** `seller_id`, `seller_zip_code_prefix`, `seller_city`, `seller_state`
- **geolocation:** `geolocation_zip_code_prefix`, `geolocation_lat`, `geolocation_lng`, `geolocation_city`, `geolocation_state`
- **translation:** `product_category_name`, `product_category_name_english` *(UTF-8 BOM on first header name observed at shell `head`; profiler normalized)*

---

## 3. Source relationships (evidence-based)

### Confirmed coverage (child keys ⊆ parent; exact column names)

| Child → Parent | Key | Child coverage in parent |
|----------------|-----|--------------------------|
| orders → customers | `customer_id` | 100% (and reverse 100%) |
| order_items → orders | `order_id` | 100% of item `order_id`s exist in orders |
| payments → orders | `order_id` | 100% |
| reviews → orders | `order_id` | 100% |
| order_items → products | `product_id` | 100% |
| order_items → sellers | `seller_id` | 100% |
| translation → products (categories used) | `product_category_name` | all 71 translation names appear in products |

### Parent gaps (orders without children)

| Gap | Count |
|-----|------:|
| Orders with no items | 775 |
| Orders with no payment | 1 |
| Orders with no review | 768 |

### Category orphans (products → translation)

2 Portuguese categories in products missing from translation: `pc_gamer`, `portateis_cozinha_e_preparadores_de_alimentos`.

### Provisional links (name-based only — not confirmed FKs)

| Link | Coverage | Orphans |
|------|----------|--------:|
| `customer_zip_code_prefix` → `geolocation_zip_code_prefix` | 98.95% | 158 |
| `seller_zip_code_prefix` → `geolocation_zip_code_prefix` | 99.64% | 8 |

### Key uniqueness (confirmed)

| Candidate | Unique? |
|-----------|:-------:|
| `orders.order_id` | yes |
| `customers.customer_id` | yes |
| `customers.customer_unique_id` | **no** (96,096 / 99,441) |
| `products.product_id` | yes |
| `sellers.seller_id` | yes |
| `(order_id, order_item_id)` | yes |
| `(order_id, payment_sequential)` | yes |
| `translation.product_category_name` | yes |
| `reviews.review_id` | **no** (789 IDs span multiple orders) |
| `geolocation_zip_code_prefix` | **no** (19,015 prefixes / 1,000,163 rows; 261,831 full-row dupes) |

---

## 4. Proposed initial database architecture (proposal only)

**Not implemented / not frozen by this gate.** Existing `database/**` drafts are provisional.

```
data/raw/*.csv  →  [Python ETL]  →  PostgreSQL
                                      ├─ raw|staging  (1:1 typed landing of source columns)
                                      └─ analytics|dw (dimensional model — Phase 5)
                                                         → Power BI (Phase 8)
```

### Recommended layers (choose naming in outstanding decisions)

| Layer | Purpose | Owner |
|-------|---------|-------|
| Immutable files | Exact Olist CSVs in `data/raw/` | Ops / DE |
| Landing | TEXT-safe or lightly typed mirror of CSV columns only | Data Engineer |
| Staging | Typed, cleaned entities; preserve source column names unless ADR | SQL Architect |
| Warehouse | Star schema dims/facts derived only from inventoried columns | SQL Architect |
| Presentation | Power BI on warehouse/marts views | BI Developer |

### Proposed entities (logical — column lists deferred to Phase 5)

| Entity | Source file(s) | Proposed grain |
|--------|----------------|----------------|
| Fact order items | items (+ order context) | `order_id` + `order_item_id` |
| Fact payments | payments | `order_id` + `payment_sequential` |
| Fact reviews | reviews | **TBD** after review-grain ADR |
| Dim order / date attrs | orders | `order_id` / calendar day |
| Dim customer | customers | Prefer `customer_unique_id` for buyer; retain `customer_id` bridge |
| Dim product | products + translation | `product_id` |
| Dim seller | sellers | `seller_id` |
| Dim geo (optional) | geolocation aggregated | zip prefix centroid — **TBD** |

No measures beyond columns that exist (`price`, `freight_value`, `payment_value`, `review_score`, counts, date diffs).

---

## 5. Implementation plan (phased)

| Phase | Name | Primary agents | Depends on |
|------:|------|----------------|------------|
| **1** | Discovery & requirements | Orchestrator, BA, DE (profile) | — |
| 2 | Architecture freeze from profile | DE, SQL Architect, Orchestrator | Phase 1 approval |
| 3 | PostgreSQL + Docker bootstrap | SQL Architect | Phase 2 |
| 4 | ETL load raw → landing/staging | Data Engineer | Phase 3 |
| 5 | Dimensional transforms | SQL Architect | Phase 4 |
| 6 | Data quality tests | QA Engineer | Phase 5 |
| 7 | KPI policy validation | Business Analyst | Phase 6 |
| 8 | Power BI dashboard | BI Developer | Phase 7 |
| 9 | Integration / E2E | QA + Orchestrator | Phase 8 |
| 10 | Docs & demo packaging | Docs Engineer + Orchestrator | Phase 9 |

---

## 6. Agent dependency map

```
Orchestrator
  ├─ Phase 1: BA (questions/KPI candidates) ∥ DE (profiling)  ← current
  ├─ Phase 2: DE + SQL Architect (architecture ADR)
  ├─ Phase 3: SQL Architect
  ├─ Phase 4: Data Engineer          [needs Phase 3 schemas]
  ├─ Phase 5: SQL Architect          [needs Phase 4 loads]
  ├─ Phase 6: QA                     [needs Phase 5 model]
  ├─ Phase 7: BA                     [needs trusted metrics]
  ├─ Phase 8: BI Developer           [needs Phase 7 KPI sign-off]
  ├─ Phase 9: QA + Orchestrator
  └─ Phase 10: Docs Engineer
```

**Hard dependency:** BI Developer must not invent measures without BA-mapped source columns.  
**Hard dependency:** SQL Architect must not add columns absent from inventoried CSVs (except technical audit columns like `_loaded_at` via ADR).

---

## 7. Acceptance criteria by phase

### Phase 1 (this gate)

- [x] Repo inspected; dataset files identified
- [x] Structure verified against actual CSV headers
- [x] Complete inventory with sizes/rows/columns
- [x] Source relationships evidenced (coverage + uniqueness)
- [x] Initial DB architecture **proposed** (not implemented as approved)
- [x] Implementation plan + agent dependencies documented
- [x] Phase acceptance criteria defined
- [x] Dataset profiling delegated to Data Engineer
- [ ] **User approval of this review**
- [ ] Specialist agent instruction files available / created under `.cursor/agents/`
- [ ] Disposition of premature `database/**`, `tests/**`, KPI freeze docs (keep as draft / revert / review)

### Phase 2

- [ ] ADR resolving schema names (`raw/staging/analytics` vs `staging/dw`)
- [ ] ADR for review grain and geolocation aggregation
- [ ] Architecture doc updated to match ADRs only
- [ ] No new invented business columns

### Phase 3

- [ ] Docker Compose Postgres up from clean clone + `.env.example`
- [ ] Schemas created idempotently
- [ ] No secrets in Git

### Phase 4

- [ ] All 9 CSVs load with row counts matching profile (± documented exclusions)
- [ ] Landing tables contain only inventoried columns (+ approved audit cols)
- [ ] Load is rerunnable

### Phase 5

- [ ] Star schema DDL + transforms merge-ready
- [ ] PK/FK rules match profile uniqueness findings
- [ ] Orphan/geo/review policies implemented per ADR

### Phase 6

- [ ] Automated tests: PK uniqueness, FK coverage, row-count reconciliation
- [ ] Failures documented or fixed

### Phase 7

- [ ] Each dashboard KPI maps to source columns + filter policy
- [ ] Explicit “not profit / not margin” limitations documented

### Phase 8

- [ ] MVP pages: executive, sales/category, geography, logistics, payments
- [ ] Measures match Phase 7 definitions

### Phase 9

- [ ] E2E: clone → env → up → load → transform → query/refresh smoke
- [ ] Critical defects closed

### Phase 10

- [ ] README runbook; architecture & decisions current; demo script

---

## 8. Assumptions

1. Scope is the **core 9** Olist ecommerce CSVs only (Marketing Funnel out — ADR-001 draft).
2. Portfolio stack intent: PostgreSQL + Python/Pandas ETL + Power BI + Docker.
3. KPI list in `docs/requirements.md` is **candidate** until Phase 7; delivered-only filter in `kpi_definitions.md` is **not yet approved**.
4. Parallel agents may have written past Phase 1; Orchestrator does not auto-approve that work.
5. Currency is BRL in source economics; no FX conversion unless later ADR.

---

## 9. Outstanding decisions (need your input)

1. **Agent files:** Create the seven `.cursor/agents/*.md` instruction files? Confirm names/scopes.
2. **Schema naming:** `raw` + `staging` + `analytics` **vs** `staging` + `dw` (+ optional `marts`).
3. **Premature artifacts:** Keep `database/**` and `tests/**` as draft starting points, or reset and rebuild after Phase 2 ADR?
4. **Review grain:** keep all review rows vs latest-per-order vs composite key including `order_id`.
5. **Geolocation:** centroid-per-prefix vs exclude from MVP facts.
6. **Power BI mode:** Import (proposed) vs DirectQuery.
7. **GMV filter policy:** all statuses vs `delivered` only (affects every commercial KPI).
8. **Missing category translations:** leave unmapped label vs manual English mapping for the 2 orphans.
9. **First git commit:** when to baseline (after Phase 1 approval recommended).

---

## 10. Approval

Reply with approval (and decisions on §9 items you want to freeze now).  
**Orchestrator will not proceed to Phase 2 implementation until you approve.**
