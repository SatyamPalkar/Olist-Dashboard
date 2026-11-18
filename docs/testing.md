# Testing

**Status:** In progress — test helpers and raw CSV ingestion tests exist; warehouse/integration/Power BI tests are largely Planned.  
**This documentation pass did not produce a green pytest run** (default system Python lacked `pytest`). Treat results as **Implemented, not Verified** until an environment with `pip install -r requirements.txt` reports pass evidence in [`progress.md`](progress.md).

---

## Goals

1. Prove raw files match the published Olist column contracts.
2. Eventually prove `raw` row counts, staging grain, analytics FKs, and KPI parity.
3. Never mark a phase **Accepted** without automated or query evidence.

---

## Layout

```
tests/
├── conftest.py
├── test_ingestion.py          # Raw CSV contract tests (Implemented)
├── fixtures/                  # Small sample CSVs for unit isolation
└── helpers/
    ├── contracts.py           # Expected columns, keys, enums
    ├── raw_loader.py          # Load from data/raw/
    ├── db.py                  # Optional Postgres helpers
    ├── metrics.py
    ├── dq_report.py
    └── transforms_reference.py
```

Also authored (SQL, not pytest):

- `database/scripts/02_data_quality_checks.sql`
- `powerbi/validation/validate_measures.sql`
- `powerbi/validation/checklist.md`

Empty placeholder: `sql/tests/` (do not fork tests there; prefer `tests/` + `database/scripts`).

---

## How to run

```bash
python -m venv .venv
source .venv/Scripts/activate   # or your platform equivalent
pip install -r requirements.txt

# All tests
pytest tests/ -q

# Raw CSV tests only
pytest tests/ -m raw -q

# Skip slow if markers used
pytest tests/ -m "not slow" -q
```

Configured in `pytest.ini`: `testpaths=tests`; markers `unit`, `integration`, `raw`, `slow`.

---

## Coverage map

| Area | Artefact | Status |
|------|----------|--------|
| Raw file presence & columns | `tests/test_ingestion.py` | Implemented |
| Declared PK uniqueness (excl. reviews) | `test_ingestion.py` | Implemented |
| Review non-uniqueness awareness | contracts / profile | Documented; assert via profile/ADR-006 |
| Orders ↔ customers row parity | `test_ingestion.py` | Implemented |
| Raw DB load smoke vs CSV counts | `tests/test_raw_load_smoke.py` | **Planned** (Phase 4 handoff) |
| Staging/mart transform tests | — | Planned |
| Live Postgres integration | `tests/helpers/db.py` + future modules | Scaffold / Planned |
| SQL DQ checks | `02_data_quality_checks.sql` | Implemented as SQL; **not Verified** live |
| DAX ↔ SQL measure parity | `powerbi/validation/*` | Authored; requires loaded warehouse + Desktop |
| E2E / Phase 9 | — | Planned |

---

## Evidence rules

| Claim | Required evidence |
|-------|-------------------|
| “Tests passed” | Paste pytest summary or CI log into `progress.md` |
| “Warehouse valid” | Row counts + DQ script output |
| “Dashboard works” | Screenshot + validation checklist ticks |
| “Pipeline automated” | Scheduler/Compose config that actually runs unattended |

Without that evidence, use: **Implemented**, **In progress**, or **Planned** — never **Verified**.

---

## Known gaps

1. No CI workflow file in repo yet.
2. No post-load pytest modules.
3. BA “delivered-only” vs BI “non-canceled” KPI filter still pending Phase 7 sign-off — tests should eventually lock the chosen rule.
