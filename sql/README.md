# SQL (pointer)

**Canonical SQL lives in `database/`.**

Do not add competing DDL here. Use:

- `database/schemas/` — DDL
- `database/staging/` — raw → staging
- `database/marts/` — staging → analytics
- `database/views/` — reporting
- `database/scripts/` — run orchestration

Contract: `database/docs/contracts_raw_staging.md` · ADR-005.
