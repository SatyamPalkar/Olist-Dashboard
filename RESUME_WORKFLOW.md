# Resume workflow — Retail BI Platform (multi-agent)

Unzip this archive, open the folder in Cursor, then continue from the status below.

> **Update, 2026-11-18:** The user subsequently authorized end-to-end development. The old Phase 1 gate is no longer a pause. Read `docs/progress.md` for current evidence: the canonical warehouse build and 129 tests passed locally; Docker and the Power BI report still need verification. Use `scripts/build_warehouse.py --rebuild`, not the incompatible provisional `etl/` loader.

## Quick start for the next LLM / Orchestrator

1. Read `docs/progress.md`, `docs/decisions.md`, `docs/phase1_orchestrator_review.md`.
2. Read agent briefs in `agents/` (Agent 0–6).
3. Optionally read prior chat history under `agent_continuity/transcripts/` (JSONL) and the index `agent_continuity/agent_index.json`.
4. Resume as **Agent 0 (Orchestrator)** unless the user assigns a specialist.
5. Next gated work: **Phase 3 Docker Postgres** → **Phase 4 ETL load** (see `docs/handoffs/`).

## Agent roster

| Agent | Brief | Prior transcript (continuity) |
|-------|-------|-------------------------------|
| 0 Orchestrator | `agents/00_orchestrator.md` | `agent_continuity/transcripts/00_orchestrator__*` |
| 1 Data Engineer | `agents/01_data_engineer.md` | Subagent under orchestrator transcripts; handoffs in `docs/handoffs/` |
| 2 SQL Architect | `agents/02_sql_architect.md` | `.../02_sql_architect__*` |
| 3 BI Developer | `agents/03_bi_developer.md` | `.../03_bi_developer__*` |
| 4 Data QA | `agents/04_data_qa_engineer.md` | `.../04_data_qa_engineer__*` |
| 5 Business Analyst | `agents/05_business_analyst.md` | `.../05_business_analyst__*` |
| 6 Documentation | `agents/06_documentation_engineer.md` | `.../06_documentation_engineer__*` |

Prompts used to start each agent are also mirrored in `agent_continuity/prompts/`.

## Current truthful status (do not claim complete)

| Layer | Status |
|-------|--------|
| Raw Olist CSVs | Present in `data/raw/` |
| Docs / ADRs / KPIs | Present under `docs/` |
| SQL star schema | Present under `database/` (`raw` / `staging` / `analytics`) |
| Python ETL load | Incomplete / partial — check `etl/` |
| Docker Postgres | Check `docker-compose.yml`; may not have been run |
| pytest (raw/unit) | Runnable: `pytest -m "not integration"` |
| Power BI `.pbix` | Not fabricated — specs under `powerbi/` |
| End-to-end demo | **Not done** until DB up + load + integration tests |

## How to re-attach specialist agents in Cursor

1. Open this project root in Cursor.
2. Start a new Agent chat.
3. Paste the contents of the relevant file from `agents/` as the first message (or `@agents/0X_....md`).
4. Point the agent at `docs/progress.md` and the matching handoff under `docs/handoffs/`.
5. For continuity, say: “Resume from transcript in `agent_continuity/transcripts/<slug>__*/` and do not redo completed artefacts.”

## Suggested resume prompt (Orchestrator)

```text
You are Agent 0: Project Orchestrator for the Olist Retail BI Platform.
Read agents/, docs/progress.md, docs/decisions.md, and agent_continuity/agent_index.json.
Do not restart Phase 1–2. Continue from Phase 3 (Postgres Docker) then Phase 4 (ETL load).
Coordinate specialists using the briefs in agents/. Keep data/raw immutable.
```

## Verify after unzip

```bash
pip install -r requirements.txt
python -m pytest -m "not integration" -q
python scripts/generate_dq_report.py
```
