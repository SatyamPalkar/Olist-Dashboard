# Database Architecture — Olist Analytics Warehouse

PostgreSQL analytical warehouse for Olist Brazilian E-Commerce (2016–2018).

## Layers

| Schema | Purpose |
|--------|---------|
| `raw` | Immutable landing of source CSVs (as ingested) |
| `staging` | Cleaned, typed, standardised business entities |
| `analytics` | Star-schema facts, dimensions, reporting views |

## Directory layout

```
database/
├── schemas/     # DDL: schemas, tables, indexes, constraints
├── staging/     # TRANSFORM: raw → staging
├── marts/       # TRANSFORM: staging → analytics dims/facts
├── seeds/       # Reference / calendar seed data
├── views/       # Reporting views, materialised views, KPI SQL
├── docs/        # Schema docs, ER, KPI definitions, contracts
└── scripts/     # Orchestration + EXPLAIN ANALYZE samples
```

## Quick start

```bash
psql -d olist_dw -f database/scripts/00_run_all.sql
```

Run order is encoded in `scripts/00_run_all.sql`. Scripts are idempotent where practical (`DROP IF EXISTS` / `CREATE OR REPLACE` / `TRUNCATE` + reload).

## Coordination

Raw and staging **table contracts** live in `docs/contracts_raw_staging.md`.  
Data Engineer owns ingestion into `raw.*`. SQL Architect owns staging transforms and the analytics layer.

## Power BI

Connect to schema `analytics`. Prefer views under `analytics.vw_*` and materialised views `analytics.mv_*`. Do not model directly on `raw` or `staging`.
