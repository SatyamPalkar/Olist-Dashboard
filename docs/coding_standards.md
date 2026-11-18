# Coding standards

Enforced by Orchestrator on all specialist deliverables.

## General

- Prefer clear, boring code over clever shortcuts.
- Avoid unnecessary dependencies.
- Do not overwrite files without reading them first.
- Do not invent Olist fields or business metrics.
- Keep changes scoped to the files listed in the task brief.

## Python

- Python 3.11+; type hints on public functions.
- Use `pathlib.Path`; configure via env / `config/defaults.yaml`.
- Pandas for tabular cleaning; SQLAlchemy or `psycopg` for DB I/O (choice locked in Phase 4 ADR).
- No hardcoded passwords/hosts.
- Tests with `pytest` under `tests/`.

## SQL

- Snake_case identifiers; schemas `raw` / `staging` / `analytics` (ADR-005).
- Canonical tree: `database/` (`schemas/`, `staging/`, `marts/`, `views/`, `scripts/`).
- Explicit column lists in `INSERT`/`CREATE TABLE AS`.
- Document grain in header comments.
- Do not fork competing DDL under `sql/`.

## Naming

| Object | Convention | Example |
|--------|------------|---------|
| Raw table | `raw.olist_*` | `raw.olist_orders` |
| Staging table | `staging.stg_*` | `staging.stg_orders` |
| Dimension | `analytics.dim_*` | `analytics.dim_customers` |
| Fact | `analytics.fact_*` | `analytics.fact_order_items` |
| View | `analytics.vw_*` / `mv_*` | `analytics.vw_reporting_kpis` |
| Python module | snake_case | `etl/load_raw.py` |

## Git

- No secrets, no raw CSVs in commits.
- Commit only when Orchestrator / user requests.

## Acceptance

Every major phase requires:

1. Automated or scripted checks.
2. Orchestrator review of diffs against the task’s allowed files.
3. Progress entry with evidence.
