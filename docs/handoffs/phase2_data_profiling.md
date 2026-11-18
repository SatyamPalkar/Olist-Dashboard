# Handoff — Phase 2: Data profiling & architecture refinement

**From:** Agent 0 (Orchestrator)  
**To:** Data Engineer (primary), SQL Architect (consult)  
**Depends on:** Phase 1 complete; nine CSVs in `data/raw/`  
**Status:** Ready to start once raw data is present

---

## Objective

Profile the Olist raw files and refine architecture assumptions with evidence (nulls, keys, cardinality, date ranges, join orphans). Produce a written profile that freezes enough detail for Phase 3 DDL.

## Dependencies

1. `docs/dataset_inventory.md` (field contract)
2. Files listed in `config/defaults.yaml` → `raw_files` present under `data/raw/`
3. ADR-001–003 accepted

## Allowed files to create/modify

- `etl/profile.py` (or package under `etl/profiling/`)
- `docs/data_profile.md` (required report)
- `tests/test_raw_profile_smoke.py` (optional but preferred)
- `requirements.txt` / `pyproject.toml` — **only** if adding pandas/pytest; justify in PR notes
- Updates to `docs/architecture.md` §4 (proposed dims/facts) — after Orchestrator review
- Updates to `docs/progress.md` — status only

**Forbidden:** DDL that invents columns; changing schema names; modifying `data/raw/` contents; Power BI artefacts; shared contract changes without ADR draft.

## Expected deliverables

1. Reproducible profiling script that reads only from `data/raw/`.
2. `docs/data_profile.md` containing at least:
   - Row counts per file
   - Null rates for PK/FK and critical timestamps
   - Uniqueness results for declared keys
   - Min/max of `order_purchase_timestamp`
   - Orphan sample counts for major FKs
   - Geolocation cardinality per zip prefix (avg/max rows)
   - Review multiplicity per `order_id`
3. Short recommendation for: review grain, geolocation aggregation, delivered-only GMV filter (input to ADR drafts).

## Acceptance criteria

- [ ] Script runs successfully against local `data/raw/`
- [ ] Report columns match inventory (no invented fields)
- [ ] Key uniqueness and orphan checks have numeric evidence
- [ ] Orchestrator can re-run script and reproduce summary numbers
- [ ] No credentials in code
- [ ] `docs/progress.md` updated after review

## Out of scope

Loading PostgreSQL, Docker Compose, Power BI, KPI final definitions.
