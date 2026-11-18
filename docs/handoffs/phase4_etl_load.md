# Handoff — Phase 4: ETL load into `raw`

**From:** Agent 0  
**To:** Data Engineer  
**Depends on:** Phase 3 acceptance; `data/raw/` nine CSVs; contracts file  
**Status:** Blocked on Phase 3

---

## Objective

Load immutable filesystem CSVs into PostgreSQL `raw.*` tables without inventing columns; preserve source spellings.

## Allowed files

- `etl/**` (create package)
- `requirements.txt` (only if new deps needed; prefer existing `psycopg`, `pandas`, `python-dotenv`)
- `tests/test_raw_load_smoke.py`
- `docs/progress.md`
- Do **not** change `database/schemas/01_raw_tables.sql` without ADR
- Do **not** write cleaned data back into `data/raw/`

## Expected deliverables

1. Idempotent load script (TRUNCATE + COPY or equivalent) for all nine tables
2. `_loaded_at` populated
3. Row-count smoke test vs CSV line counts (minus header)
4. README section: how to run load

## Acceptance criteria

- [ ] Row counts match profile (±0) for each raw table
- [ ] Column sets match `database/docs/contracts_raw_staging.md`
- [ ] Re-run does not duplicate rows
- [ ] No credentials in source
