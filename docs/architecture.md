# Architecture — Retail BI Platform

**Status:** Active (ADR-005)  
**Last updated:** 2026-11-18

---

## 1. System overview

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────────────┐
│  Olist CSVs     │────▶│  Python ETL      │────▶│  PostgreSQL                │
│  (data/raw/)    │     │  (Pandas / COPY) │     │  raw → staging → analytics │
└─────────────────┘     └──────────────────┘     └─────────────┬──────────────┘
                                                               │
                                                               ▼
                                                      ┌─────────────────┐
                                                      │  Power BI       │
                                                      │  Import mode    │
                                                      └─────────────────┘
```

**Principles**

- Filesystem raw CSVs in `data/raw/` are immutable.
- Database `raw` schema is the landing zone (TEXT columns + `_loaded_at`).
- `staging` holds cleaned typed entities; `analytics` holds the star schema.
- Credentials only via environment variables.
- Shared DB contracts change only via ADR in `docs/decisions.md`.

---

## 2. Logical layers

| Layer | Location | Purpose | Owner |
|-------|----------|---------|-------|
| Filesystem raw | `data/raw/` | Exact Olist CSVs | Operator / DE |
| DB raw | PostgreSQL `raw` | Immutable landing | Data Engineer |
| Staging | PostgreSQL `staging` | Cleaned entities | SQL Architect |
| Analytics | PostgreSQL `analytics` | Dims, facts, views | SQL Architect |
| Presentation | Power BI | Dashboards & DAX | BI Developer |

Canonical SQL artefacts: **`database/`**  
(`sql/` is a pointer only — do not fork DDL there.)

---

## 3. Source system (Olist)

Nine files — see `docs/dataset_inventory.md` and profile evidence in `docs/data_profile.md`.

Join spine: **orders** ← customers, items, payments, reviews; items → products, sellers; zip prefixes → geolocation (aggregated).

---

## 4. Dimensional model (implemented in DDL)

| Table | Type | Grain |
|-------|------|-------|
| `analytics.dim_date` | Dimension | One calendar day |
| `analytics.dim_geography` | Dimension | One zip prefix |
| `analytics.dim_customers` | Dimension | `customer_unique_id` |
| `analytics.dim_products` | Dimension | `product_id` |
| `analytics.dim_sellers` | Dimension | `seller_id` |
| `analytics.fact_orders` | Fact | One order |
| `analytics.fact_order_items` | Fact | One order line |
| `analytics.fact_payments` | Fact | One payment sequence |
| `analytics.fact_order_reviews` | Fact | One review row (`review_sk`) |

DDL: `database/schemas/03_analytics_tables.sql`  
Transforms: `database/staging/`, `database/marts/`  
Contracts: `database/docs/contracts_raw_staging.md`

**Acceptance status:** DDL/SQL reviewed for alignment with profile; **not** accepted as “complete” until Docker + load + automated tests execute successfully (Phases 3–6).

---

## 5. Technology choices

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Store | PostgreSQL | Portable, Docker-friendly, Power BI compatible |
| ETL | Python + COPY/`psycopg` | Controllable cleaning; portfolio clarity |
| Orchestration | Docker Compose + scripts | Reproducible local demo (**not yet present**) |
| BI | Power BI Desktop Import | Employer-relevant; ADR-004 |
| Config | `.env` + `config/` | No secrets in Git |

---

## 6. Repository layout

```
satyam_project/
├── config/
├── data/raw/              # immutable Olist CSVs (gitignored content)
├── database/              # CANONICAL SQL (schemas, staging, marts, views)
├── docs/
├── etl/                   # Python load jobs (Phase 4 — thin today)
├── scripts/               # profiling / analysis helpers
├── tests/                 # pytest (Phase 6 — scaffolding only)
├── powerbi/               # semantic model docs + build guides
├── .env.example
└── README.md
```

---

## 7. Integration contracts (protected)

Agents **must not** change without Orchestrator ADR:

1. Schema names: `raw`, `staging`, `analytics` (ADR-005).
2. Env vars: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`.
3. Raw CSV filenames (nine Olist files).
4. Analytics table names listed in §4.
5. Raw/staging column contracts in `database/docs/contracts_raw_staging.md`.

---

## 8. Open / next integration gaps

1. No `docker-compose.yml` yet — Phase 3 incomplete as a runnable system.
2. No Python ETL that loads `data/raw/` → `raw.*` yet — Phase 4 gap.
3. Pytest raw tests authored; suite not Verified in all environments — Phase 6 gap.
4. Power BI docs exist; `.pbix` / live connection not verified — Phase 8 incomplete.
5. Documentation suite for hire/reproduce path: see root README index (`setup`, `etl_documentation`, `database_schema`, `bi_documentation`, etc.).
