# Handoff — Phase 3: PostgreSQL + Docker

**From:** Agent 0  
**To:** SQL Architect (DDL owner) + Data Engineer (compose/ops)  
**Depends on:** ADR-005; `database/schemas/*` present  
**Status:** Ready

---

## Objective

Make PostgreSQL runnable via Docker Compose and apply existing DDL so `raw` / `staging` / `analytics` exist on a fresh machine.

## Allowed files

- `docker-compose.yml` (create)
- `Dockerfile` only if justified (prefer official `postgres:16` image)
- `.env.example` (extend, no secrets)
- `scripts/init_db.sh` or `scripts/apply_ddl.py` (optional)
- `docs/progress.md` (status note)
- Do **not** rename schemas or alter contracts without ADR

## Expected deliverables

1. `docker compose up -d` starts Postgres with credentials from `.env`
2. Init applies `database/schemas/00_create_schemas.sql` … `04_indexes.sql` (or documents exact apply command)
3. Smoke check: `\dn` shows `raw`, `staging`, `analytics`

## Acceptance criteria

- [ ] Compose file uses env vars (no hardcoded passwords in YAML beyond variable substitution)
- [ ] Fresh volume → schemas/tables created
- [ ] Command documented in README
- [ ] Orchestrator can reproduce without manual SQL editing
