# Data QA — pytest suite

**Owner:** Agent 4 (Data QA Engineer)

## Modules

| File | Scope |
|------|--------|
| `test_ingestion.py` | Raw file availability, columns, types, nulls, keys, dates, domains |
| `test_transformations.py` | Staging-rule oracle, idempotency, missing/duplicate handling |
| `test_database.py` | PK/FK, constraints, fact grain (integration / Postgres) |
| `test_data_quality.py` | Orphans, multiplicity, double-counting probes |
| `test_reconciliation.py` | Python ↔ SQL totals; payment vs merchandise gap |
| `test_business_metrics.py` | Orders, GMV, freight, payments, AOV, delivery, reviews |

## Markers

```bash
pytest -m "unit and raw"     # offline raw validation (default CI smoke)
pytest -m integration        # needs POSTGRES_* + loaded warehouse
pytest -m "not integration"  # skip DB tests
```

## Reports

```bash
python scripts/generate_dq_report.py
# → reports/data_quality_report.json
# → docs/data_quality_report.md
```

## Fixtures

Documented synthetic CSVs under `tests/fixtures/` plus `baselines.json` regression totals.  
See `docs/known_data_limitations.md` for accepted exceptions.
