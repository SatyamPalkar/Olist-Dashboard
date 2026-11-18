# Retail BI Platform — Project Plan

**Project:** Olist Retail Business Intelligence Platform  
**Stack:** PostgreSQL · Python · Pandas · SQL · Power BI · Docker · Git  
**Dataset:** [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)  
**Orchestrator:** Agent 0 (Lead DE / BI Architect)  
**Status:** Phase 2 accepted; Phase 3 next (Docker runtime)

---

## Specialist agents

| Agent | Scope |
|-------|--------|
| Data Engineer | Ingestion, cleaning, ETL |
| SQL Architect | PostgreSQL, modelling, SQL |
| BI Developer | Power BI, DAX, dashboards |
| QA Engineer | Validation, automated tests |
| Business Analyst | Requirements, KPIs, insights |
| Documentation Engineer | Technical & business docs |

---

## Phases

| Phase | Name | Owner(s) | Status | Dependencies |
|-------|------|----------|--------|--------------|
| 1 | Requirements & dataset discovery | Orchestrator, BA | **Accepted** | None |
| 2 | Data profiling & architecture | Data Engineer, SQL Architect | **Accepted** | Phase 1 |
| 3 | PostgreSQL setup | SQL Architect + DE | **In progress (DDL yes / runtime no)** | Phase 2 |
| 4 | ETL development | Data Engineer | Pending | Phase 3 |
| 5 | SQL transforms & dimensional model | SQL Architect | **SQL authored; await execution** | Phase 4 |
| 6 | Data quality testing | QA Engineer | Pending | Phase 5 |
| 7 | Business analysis & KPI validation | Business Analyst | Draft only | Phase 6 |
| 8 | Power BI development | BI Developer | Design docs only | Phase 7 |
| 9 | Integration & E2E testing | QA + Orchestrator | Pending | Phase 8 |
| 10 | Documentation & deployment | Docs Engineer + Orchestrator | **In progress** — docs suite Implemented; Compose deploy Planned | Phase 9 for full deploy DoD |

---

## Active tasks

### T1.1 — Project bootstrap & governance
- **Objective:** Establish repo layout, PM docs, coding standards, and env safety.
- **Dependencies:** None
- **Expected deliverables:** `docs/*`, folder scaffold, `.gitignore`, `.env.example`, `README.md`
- **Acceptance criteria:**
  - [x] PM docs exist and link phases to owners
  - [x] Raw data path is immutable (`data/raw/` gitignored for CSVs)
  - [x] No credentials in source; env vars documented
  - [x] Git repo initialized with baseline structure
- **Status:** Complete

### T1.2 — Dataset inventory & field contract
- **Objective:** Document every Olist CSV, primary/foreign keys, and join graph without inventing fields.
- **Dependencies:** T1.1
- **Expected deliverables:** `docs/dataset_inventory.md`, `docs/data_acquisition.md`
- **Acceptance criteria:**
  - [x] All 9 official files listed with documented columns
  - [x] Join relationships match Olist public schema
  - [x] Out-of-scope metrics explicitly excluded
- **Status:** Complete

### T1.3 — Business requirements & KPI candidates
- **Objective:** Define stakeholder questions and KPI candidates grounded only in available fields.
- **Dependencies:** T1.2
- **Expected deliverables:** `docs/requirements.md`
- **Acceptance criteria:**
  - [x] Each KPI maps to source columns / transforms
  - [x] No invented metrics
- **Status:** Complete

### T1.4 — Operator data download (human)
- **Objective:** Place nine Olist CSVs in `data/raw/`.
- **Dependencies:** T1.2
- **Expected deliverables:** Files on disk per `docs/data_acquisition.md`
- **Acceptance criteria:**
  - [x] All nine filenames present and readable
- **Status:** Complete

### T2.1 — Data profiling
- **Objective:** Profile raw CSVs (nulls, keys, cardinality, date ranges).
- **Dependencies:** T1.4
- **Deliverables:** `scripts/profile_olist_csvs.py`, `docs/data_profile.md`
- **Acceptance criteria:** Met (row counts, nulls, key uniqueness, orphans, date range) — ADR-006
- **Status:** Accepted

### T3.1 — Dockerised PostgreSQL + apply DDL
- **Objective:** Runnable Postgres with `raw`/`staging`/`analytics`.
- **Dependencies:** ADR-005; existing `database/schemas/*`
- **Handoff:** `docs/handoffs/phase3_postgres_docker.md`
- **Status:** Ready / in progress

### T4.1 — Load CSVs → `raw.*`
- **Objective:** Idempotent Python/COPY load with row-count tests.
- **Dependencies:** T3.1
- **Handoff:** `docs/handoffs/phase4_etl_load.md`
- **Status:** Blocked on T3.1

---

## Definition of done (portfolio)

A phase is complete only when:

1. Deliverables exist and were reviewed by Orchestrator.
2. Acceptance criteria are checked with evidence (tests, queries, or review notes).
3. Integration contracts (schemas, env vars, table names) are unchanged without an ADR in `docs/decisions.md`.
4. `docs/progress.md` is updated.

**Final DoD:** Reproducible Docker + ETL + dimensional warehouse + Power BI semantic model + tests + docs that an employer can clone and demonstrate.
