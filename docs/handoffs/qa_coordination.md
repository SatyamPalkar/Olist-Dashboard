# QA coordination notes

**From:** Agent 4 (Data QA Engineer)  
**To:** SQL Architect, Business Analyst, Data Engineer, Orchestrator  
**Date:** 2026-11-18

## Delivered

- Pytest suite under `tests/` (6 required modules + helpers + fixtures)
- `docs/known_data_limitations.md` — quantified exceptions KX-001…KX-009
- `docs/data_quality_report.md` + `reports/data_quality_report.json`
- Offline result: **87 passed**, integration tests skipped until warehouse load

## Needs from partners

| Partner | Ask |
|---------|-----|
| Orchestrator | ADR update for schema names: implemented `raw`/`staging`/`analytics` vs ADR-003 `dw` |
| SQL Architect | Confirm review grain (all rows in `fact_order_reviews`; latest on `fact_orders.review_score`) — already coded; please ADR |
| Business Analyst | Sign off filter policy (all statuses vs delivered-only) for GMV / AOV; QA will not invent the rule |
| Data Engineer | When ETL lands, keep raw immutable; expose load entrypoint so `test_transformations.test_etl_package_hook_when_present` can import it |

## Do not change

- Source CSVs to force green tests
- KPI definitions without BA/SQL agreement
- Silent drops of orphan/gap orders (775 no-item orders are retained by design)

## How to re-run

```bash
pip install -r requirements.txt
python -m pytest -m "not integration"
python scripts/generate_dq_report.py
# After Postgres load:
python -m pytest -m integration
```
