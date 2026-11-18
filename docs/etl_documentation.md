# ETL documentation

**Overall pipeline status**

| Stage | Status |
|-------|--------|
| Source CSVs on disk | Implemented (local; gitignored) |
| Extract / load into `raw.*` | **Planned** (manual `\copy` documented; Python `etl/` not built) |
| Staging transforms (SQL) | **Implemented** (scripts authored; not executed live here) |
| Analytics marts (SQL) | **Implemented** (scripts authored; not executed live here) |
| Scheduled automation (Airflow/cron) | **Not planned** for MVP — runs are manual |
| Logging framework | **Partial** — SQL `\echo`; Python profiling logs to stdout/files; no central ETL logger yet |

---

## Source files

Nine Olist CSVs under `data/raw/` (immutable). Filenames and columns: [`dataset_inventory.md`](dataset_inventory.md), contracts: [`../database/docs/contracts_raw_staging.md`](../database/docs/contracts_raw_staging.md).

| Raw table | Source file |
|-----------|-------------|
| `raw.olist_orders` | `olist_orders_dataset.csv` |
| `raw.olist_order_items` | `olist_order_items_dataset.csv` |
| `raw.olist_order_payments` | `olist_order_payments_dataset.csv` |
| `raw.olist_order_reviews` | `olist_order_reviews_dataset.csv` |
| `raw.olist_customers` | `olist_customers_dataset.csv` |
| `raw.olist_products` | `olist_products_dataset.csv` |
| `raw.olist_sellers` | `olist_sellers_dataset.csv` |
| `raw.olist_geolocation` | `olist_geolocation_dataset.csv` |
| `raw.product_category_name_translation` | `product_category_name_translation.csv` |

---

## Extraction process

1. Operator downloads dataset per [`data_acquisition.md`](data_acquisition.md).
2. Files are placed in `data/raw/` without renaming or in-place cleaning.
3. **Planned:** Python job in `etl/` reads `OLIST_RAW_DIR` (default `data/raw`) and loads via `COPY`/`psycopg`.
4. **Current workaround (manual):** after `01_raw_tables.sql`, use `psql` `\copy` as in the contracts doc (paths must point at `data/raw/...`).

Handoff for the Python loader: [`handoffs/phase4_etl_load.md`](handoffs/phase4_etl_load.md).

---

## Cleaning rules

Applied primarily in **staging SQL** (not by mutating files on disk).

| Rule | Where | Behaviour |
|------|-------|-----------|
| Trim whitespace on keys/IDs | staging transforms | `TRIM(...)` |
| Empty string → NULL on timestamps | `stg_orders` etc. | `NULLIF(TRIM(...),'')::TIMESTAMP` |
| Lowercase status / payment type | staging | Normalise categoricals |
| Derive delivery metrics | `stg_orders` | `delivery_days`, `is_late_delivery`, `is_delivered`, `is_canceled` |
| Collapse geolocation | `stg_geolocation` | One row per zip; AVG lat/lng |
| Review surrogate | `stg_order_reviews` | `review_sk`; keep all rows |
| Correct `*_lenght` spellings | products staging/mart | Rename to `*_length` in typed layers |
| Join English category | products staging | Left join translation |
| Drop rows missing required keys | staging WHERE clauses | e.g. orders require order_id, customer_id, purchase timestamp |
| Conflict handling | some inserts | `ON CONFLICT ... DO NOTHING` |

Raw layer does **not** clean business values — TEXT landing only.

---

## Transformation logic

### Staging (`database/staging/`)

Orchestrator: `run_staging.sql` order:

1. Category translation  
2. Geolocation  
3. Customers, sellers, products  
4. Orders, order_items, order_payments, order_reviews  

Pattern: `BEGIN` → `TRUNCATE ... CASCADE` → `INSERT ... SELECT` from `raw.*` → `COMMIT`.

### Analytics marts (`database/marts/`)

Orchestrator: `run_marts.sql` order:

1. Seeds: Brazilian states, `dim_date`  
2. `dim_geography` → `dim_customers` → `dim_products` → `dim_sellers`  
3. `fact_orders` → `fact_order_items` → `fact_payments` → `fact_order_reviews`  

Order-fact measures are **pre-aggregated** from staging items/payments to protect grain.

### Views

- `database/views/vw_reporting_kpis.sql` — reporting KPI views  
- `database/views/mv_monthly_sales.sql` — materialised monthly aggregates (refresh after mart rebuild)

---

## Loading strategy

| Layer | Strategy | Idempotency |
|-------|----------|-------------|
| `raw` | Planned: `TRUNCATE` + `COPY` all nine tables | Re-run replaces all raw rows |
| `staging` | `TRUNCATE` + `INSERT` | Full rebuild each run |
| `analytics` | Truncate/reload dims & facts via mart scripts | Full rebuild; seeds reload |

**No incremental/CDC load** in MVP. Full reload is acceptable for ~100k orders.

Credentials: environment variables only (`POSTGRES_*`). Never hard-code passwords in ETL scripts.

---

## Error handling

| Layer | Current behaviour |
|-------|-------------------|
| Manual `\copy` / `psql -v ON_ERROR_STOP=1` | Stops on first SQL error |
| Staging/mart SQL | Transactional `BEGIN`/`COMMIT` per script file |
| Python load (`etl/`) | **Planned** — expected: fail fast on missing file, schema mismatch, or row-count drift |
| DQ SQL | `database/scripts/02_data_quality_checks.sql` authored; **not Verified** live |

There is **no** automatic retry, dead-letter queue, or partial-commit recovery for failed mid-pipeline loads. Operator re-runs from a clean step after fixing the cause.

---

## Logging

| Component | Logging |
|-----------|---------|
| `psql` runners | `\echo` step banners in `run_staging.sql`, `run_marts.sql`, `00_run_all.sql` |
| Profiling scripts | stdout + markdown/JSON under `docs/` |
| `logs/` directory | Reserved; **no** standardised ETL log writer yet |
| Future `etl/` package | Should log start/end, per-table row counts, duration, and failures to `logs/` (Planned) |

---

## How to rerun the pipeline

### A. Full build (after Postgres exists)

1. Ensure nine CSVs are in `data/raw/`.
2. Apply schemas / or run through raw DDL.
3. **Load raw** (manual `\copy` or future `python -m etl.load_raw`).
4. Run:

   ```bash
   psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
     -v ON_ERROR_STOP=1 -f database/scripts/00_run_all.sql
   ```

   If `00_run_all.sql` re-applies raw DDL mid-script, load raw **after** `01_raw_tables.sql` and before staging (follow script `\echo` notes).

### B. Analytics refresh only (raw already correct)

```bash
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -v ON_ERROR_STOP=1 -f database/scripts/01_refresh_analytics.sql
```

### C. Re-profile sources (no database)

```bash
python scripts/profile_olist_csvs.py
```

### D. Power BI

After `analytics` is populated: Desktop **Refresh** (Import mode). See [`bi_documentation.md`](bi_documentation.md).

---

## What is not automated

- Docker bring-up  
- Python raw load  
- Nightly schedules  
- Automatic Power BI Service refresh  
- End-to-end CI green pipeline  

Documenting these as **manual** is intentional until Phases 3–4 and 10 land.
