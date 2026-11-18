# Setup guide

**Status:** Canonical load and warehouse tested on local PostgreSQL; Docker Compose and Power BI Desktop remain unverified.

---

## Prerequisites

| Tool | Required for | Notes |
|------|--------------|-------|
| Git | Clone | — |
| Python 3.11+ | Profiling, BA, tests, future ETL | 3.13 observed on author machine |
| pip / venv | Dependencies | Use `requirements.txt` |
| PostgreSQL 14+ | Warehouse | Local PostgreSQL or Docker Compose |
| psql client | Running SQL scripts | Same major version as server preferred |
| Power BI Desktop | Report build | Windows; **Planned** `.pbix` |
| Kaggle account / CLI | CSV download | Optional if files already present |

---

## 1. Clone and Python environment

```bash
git clone <repository-url> satyam_project
cd satyam_project

python -m venv .venv
# Windows (Git Bash): source .venv/Scripts/activate
# Windows (cmd): .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
```

### Dependencies (`requirements.txt`)

| Package | Purpose |
|---------|---------|
| `pandas`, `numpy` | Profiling / offline analysis |
| `PyYAML` | `config/defaults.yaml` |
| `pytest` | Automated tests |
| `psycopg[binary]` | Future DB load / DB tests |
| `python-dotenv` | Load `.env` |

---

## 2. Environment variables

Copy the example file and edit locally:

```bash
cp .env.example .env
```

| Variable | Example | Purpose |
|----------|---------|---------|
| `POSTGRES_HOST` | `localhost` | Database host |
| `POSTGRES_PORT` | `5432` | Database port |
| `POSTGRES_DB` | `olist_bi` | Database name |
| `POSTGRES_USER` | `olist` | Login role |
| `POSTGRES_PASSWORD` | `change_me` | Secret — never commit |
| `OLIST_RAW_DIR` | `data/raw` | Optional override for CSV directory |

**Rules**

- `.env` is gitignored (ADR-002).
- Do not put secrets in SQL, M scripts, theme JSON, or docs.
- Kaggle credentials belong in `~/.kaggle/kaggle.json` only — never in this repo.

Non-secret defaults (schema names, file list): `config/defaults.yaml`.

---

## 3. Acquire raw data

Follow [`data_acquisition.md`](data_acquisition.md). After download, confirm:

```
data/raw/olist_customers_dataset.csv
data/raw/olist_geolocation_dataset.csv
data/raw/olist_order_items_dataset.csv
data/raw/olist_order_payments_dataset.csv
data/raw/olist_order_reviews_dataset.csv
data/raw/olist_orders_dataset.csv
data/raw/olist_products_dataset.csv
data/raw/olist_sellers_dataset.csv
data/raw/product_category_name_translation.csv
```

CSV contents are **gitignored**. Only `.gitkeep` is tracked under `data/raw/`.

Smoke check without Postgres:

```bash
python scripts/discover_olist.py
```

---

## 4. PostgreSQL

Start the Compose service with `docker compose up -d` after configuring `.env`, or use an existing **dedicated** PostgreSQL database. The Compose service has not been tested on this machine.

From the project root, set connection variables for both `psql` and the integration tests (Unix shell):

```bash
set -a
. ./.env
set +a
export PGHOST="$POSTGRES_HOST" PGPORT="$POSTGRES_PORT" PGDATABASE="$POSTGRES_DB"
export PGUSER="$POSTGRES_USER" PGPASSWORD="$POSTGRES_PASSWORD"
python scripts/build_warehouse.py --rebuild
python -m pytest -q
```

The rebuild replaces all project `raw`, `staging`, and `analytics` tables. Use a dedicated database. It validates CSV headers and logical CSV row counts before loading; each raw table is reconciled before transforms run. The build has multiple committed phases, so a failure can leave a partially rebuilt warehouse. Fix the cause and rerun the rebuild. The separate `etl/` package uses a different schema and is not the canonical load path.

BI grants (after analytics exists): see `powerbi/CONNECTION.md`.

---

## 5. Verify install pieces independently

| Check | Command / action | Expected |
|-------|------------------|----------|
| Python deps | `python -c "import pandas,yaml,dotenv"` | No import error |
| Raw files | `python scripts/discover_olist.py` | Nine files listed |
| Profile | `python scripts/profile_olist_csvs.py` | Updates `docs/data_profile.md` |
| Tests | `pytest tests/ -q` | Requires pytest installed; see [`testing.md`](testing.md) |
| Postgres | `psql -h ... -c 'SELECT 1'` | **Only if** DB is running |
| Power BI | Open Desktop → connect per CONNECTION.md | **Only after** analytics loaded |

Do not claim end-to-end success until Docker/load/tests/Power BI evidence exists in [`progress.md`](progress.md).

---

## 6. Repository hygiene

| Item | Policy |
|------|--------|
| Secrets | `.env` only |
| Raw CSVs | Local only; gitignored |
| Processed data | `data/processed/` gitignored |
| PBIX backups | `*.pbix.bak` ignored |
| Large dumps | `*.sql.gz`, `backups/` ignored |

See root `.gitignore`.
