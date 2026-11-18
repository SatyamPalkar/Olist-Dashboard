# Progress log

Track phase status, evidence, and blockers. Update after every accepted or rejected deliverable.

**Status vocabulary:** Planned · In progress · Implemented · Tested · Verified

---

## Current status

The user authorized end-to-end development on 2026-11-18, superseding the earlier Phase 1 pause. Provisional artefacts still require review where noted below.

| Area | Status | Evidence / remaining work |
|------|--------|---------------------------|
| CSV → PostgreSQL warehouse | **Tested locally** | `scripts/build_warehouse.py --rebuild`; two successful builds using PostgreSQL 17 in an isolated temporary cluster |
| Data reconciliation | **Tested locally** | Raw/fact orders 99,441; items 112,650; payments 103,886; reviews 99,224. All nine source/raw counts checked. |
| Automated tests | **Tested locally** | 129 passed, 1 pandas DBAPI warning, including integration tests, after the second build. |
| Docker Compose | **Implemented; unverified** | Docker unavailable on this machine; removed obsolete SQL init mount. |
| Tableau dashboard | **Validated (generated → opened → validated); click/hover QA pending** | `tableau/Olist Executive Dashboard.twbx`: 4 pages (Executive Overview, Delivery Diagnostics, Seller & Fulfilment, Action Queue), 28 sheets, 7 single-grain extracts. 0 schema errors, 0 query errors, expected mark counts (Tableau logs). Full-canvas screenshots in `tableau/screenshots/` pass visual QA. Filter action, nav buttons and tooltips not yet click/hover-tested. Spec + QA: `docs/tableau_build_spec.md`. |
| Power BI | **Not complete (superseded by Tableau)** | Specs exist, but no report built. Power BI unavailable; user chose Tableau. |
| KPI policy | **Decided for dashboard** | ADR-007: delivered orders only. Older BI drafts that use non-canceled sales are not aligned yet. |
| End-to-end demonstration | **Mostly complete** | CSV → PostgreSQL → extracts → Tableau runs locally. Persistent PostgreSQL/Docker are still unverified, and the warehouse used is a temporary `/tmp` cluster. |

The local test cluster is temporary and does not establish a persistent Power BI connection. The old `etl/` package targets a different schema; use the canonical rebuild script. A rebuild replaces project warehouse data and is not atomic across all phases.

---

## Chronological log

### 2026-11-18 — Orchestrator bootstrap + Phase 1

- Empty repo → Git init, PM docs, scaffold, inventory, requirements.

### 2026-11-18 — Parallel specialist artefacts

Inspected (not overwritten):

- All nine CSVs in `data/raw/` (row counts match profile).
- Profiling: `scripts/profile_olist_csvs.py` → `docs/data_profile.md`.
- SQL Architect tree: `database/` with `raw` / `staging` / `analytics`.
- Power BI design docs under `powerbi/`.
- BA/helper scripts under `scripts/`.

**Contract conflict resolved:** ADR-005 adopts `raw`/`staging`/`analytics` and `database/` as canonical (supersedes draft `dw`/`marts`).

**Phase 2 acceptance evidence (sample):**

| Check | Result |
|-------|--------|
| Orders rows | 99,441 |
| Purchase timestamp range | 2016-09-04 → 2018-10-17 |
| `review_id` unique? | No (814 dup rows) |
| Geo rows / distinct zips | 1,000,163 / 19,015 |
| Item→product orphans | 0 |
| Customer zip→geo coverage | 98.95% (158 orphan prefixes) |

### 2026-11-18 — Orchestrator Phase 1 HARD GATE

- User instruction: execute **Phase 1 only**; wait for approval before proceeding.
- Delivered: inventory refresh, relationship evidence, architecture proposal, plan, agent deps, phase ACs → `docs/phase1_orchestrator_review.md`.
- Data Engineer profiling accepted as Phase 1 evidence: [Data Engineer](35372a81-f2c9-41f5-bfcf-6210bbd59d5a).
- **`.cursor/agents/` missing** (`.cursor` is an empty file) — outstanding decision.
- Supersedes any parallel “accept Phase 1–2 / start Phase 3” notes until the user explicitly approves.

### 2026-11-18 — Documentation Engineer (Agent 6)

Delivered / refreshed:

| Artefact | Status |
|----------|--------|
| Root `README.md` (portfolio presentation) | Implemented |
| `docs/dataset_profiling.md` | Implemented |
| `docs/data_dictionary.md` | Implemented |
| `docs/database_schema.md` | Implemented |
| `docs/etl_documentation.md` | Implemented |
| `docs/setup.md` | Implemented |
| `docs/testing.md` | Implemented |
| `docs/bi_documentation.md` | Implemented |
| `docs/recommendations.md` | Implemented |
| `docs/limitations_assumptions.md` | Implemented |
| Existing `architecture.md`, `project_plan.md`, `decisions.md` | Retained / cross-linked |

**Accuracy notes recorded in docs:**

- No claim that Docker, Python raw ETL, live warehouse execution, or `.pbix` works.
- Offline BA KPI baselines cited only from CSV analysis artefacts.
- pytest: modules present; **not Verified** this session (`No module named pytest` on default interpreter before venv install).

---

### 2026-11-18 — Tableau executive dashboard

- Temporary cluster `/tmp/olist_codex_pg` (port 55439) was running; delivered-order KPIs recomputed in SQL match `docs/business_insights.md`.
- Added `tableau/export_tableau_data.sql` (three single-grain extracts) and `tableau/build_tableau_workbook.py` (generates `.twb`/`.twbx` as XML instead of UI automation, which had crashed Tableau earlier).
- Fixed delivery-timing buckets so that 1,292 orders late by timestamp but delivered on the estimated date are labelled late.
- First generated workbook failed Tableau schema validation (`computed-sort`, layout attributes, window content). Fixed; second version opens and all sheets query without errors (evidence: Tableau Desktop logs).
- User's existing `Olist Retail Analytics - Draft.twb` / `- Dashboard.twb` and recovery files were left untouched.
- Redesigned to a dark theme at the user's request (reference: dark Tableau Public viz): sidebar takeaways, KPI cards with sparklines and Jan-Aug YoY comparisons, sales + late-rate trend, ranked lists. The `.twbx` opens with no load or query errors.
- Open items at that point: human visual review/screenshot (since done; see the later entry).

### 2026-11-18 — Tableau agent: diagnostics, action view, navigation, visual QA

- Wrote `docs/tableau_build_spec.md`: decision brief, data readiness, KPI contract, verified findings, worksheet spec, interactions, generator lessons, QA table.
- New grain-safe extract `order_categories.csv` (one row per delivered order × category, 97,276 rows). Appended to `tableau/export_tableau_data.sql` and run against `olist_test`. Reconciles exactly to orders/items (R$13,221,498.11; 110,197 lines; 0 flag mismatches).
- `build_tableau_workbook.py` (stdlib) now generates 3 dashboards (1440 × 840) with sidebar navigation buttons, tooltips on every chart, **Delivery Diagnostics** (region × month heatmap, state rate-vs-volume scatter, category late rate/review) and **Action Queue** (state exception table ranked by excess late orders with Priority/Watch/Monitor tiers, filter action to a monthly trend, playbook).
- Fixed the coordinator-reported visual defects:
  - Review colours: categorical palette maps are ignored, so the generator now uses numeric colour codes with custom palettes.
  - Ranked-label overlap: fixed by data-driven axis headroom.
  - Truncated sales axis: R$M measure.
  - Field-label headers: hidden.
  - Collapsed KPI text: flow children are now fixed-size.
- Datasources are now written in Tableau's canonical object-model form, so no migration runs on open.
- Validation: Tableau logs show 0 schema errors, 0 query errors and the expected marks (heatmap 100, scatter 21, categories 22, action 21, etc.). Window screenshots of all three pages at full size confirm the layout. Final instance left open; superseded instances that the agent launched were closed.
- New headline figures (verified with Python on the extracts):
  - Six Priority states hold 1,176 excess late orders, RJ 663 (56%).
  - Mar 2018 was 19%+ late in every region (NE 36.3%, N 39.2%).
  - Categories with 1,000+ orders span 5.5–9.8% late, vs 5.0–23.9% for states.
- Open: click/hover QA of the filter action, nav buttons and tooltips; business confirmation of the owner and tier thresholds.

### 2026-11-18 — Tableau agent: Seller & Fulfilment page, retention and instalment panels, portfolio screenshots

- **Carrier hand-off date** (`staging.stg_orders.order_delivered_carrier_date`), profiled on the 96,478 delivered orders:
  - 2 null; 165 before purchase; 1,350 before approval; 23 after delivery; 8 with no delivery date.
  - Timing uses the 96,281 orders where purchase ≤ hand-off ≤ delivery (197 excluded). Dispatch is measured from purchase.
- **New grain-safe extracts** (SQL appended to `tableau/export_tableau_data.sql`; only the new blocks were run):
  - `order_fulfilment.csv` (order grain).
  - `order_sellers.csv` (order × seller; 1,275 multi-seller orders counted once per seller; includes a SQL seller excess rank).
  - `customers.csv` (customer grain).
  - `card_orders.csv` (order grain; MAX card instalments; 2 zero-instalment orders excluded).
  - All reconcile to `orders.csv` with 0 mismatches. The card extract matches an independent Python computation from `payments.csv`.
- **New 4th dashboard "Seller & Fulfilment":** dispatch vs transit (late vs on-time orders), late rate by missed shipping limit, routes (500+), seller states (300+), and a top-15 seller exception list (sellers with 100+ seller-orders).
  - Headline: late orders lose most of their time in carrier transit. Late orders spend 5.8 days in dispatch + 25.7 in transit; on-time orders 3.0 + 7.9; about 86% of the extra 20.6 days is transit.
- **Delivery Diagnostics:**
  - Retention panel: repeat rate 3.19% when the first order was late vs 4.04% on time; first orders before Mar 2018; association.
  - Credit-card instalments panel: shares 33.2 / 29.8 / 21.2 / 15.4 / 0.4%; AOV R$101 → R$333 (1x → 7–10x); review and late rate by band labelled as association.
- **Cosmetic fixes:**
  - Action Queue tier moved to its own column; bar labels are numbers only.
  - Trend axes fixed to Jan 2017 – Aug 2018.
  - Long state names shown in full.
  - Scatter label overlap culled.
  - Seller and instalment headers widened.
  - Sidebar text trimmed so footers fit.
  - Navigation now has 4 buttons per page.
- **Validation:** every page opened in Tableau; logs show 0 schema errors, 0 query errors and the expected marks. Final full-canvas screenshots are in `tableau/screenshots/`.
- **Docs updated:** root `README.md` (summary, "What this project demonstrates", screenshots, verified insights, how to run), `tableau/README.md`, `docs/tableau_build_spec.md`, and an ADR-008 amendment (seven extracts).
- **Side effects:**
  - Killing an earlier validation instance (PID 63747) left Tableau recovery file `tableau/.~Olist Executive Dashboard__63747.twbr`. It is git-ignored. Tableau reopens it as "[Recovered]" on each launch; close that window without saving to clear it.
  - Tableau's window-placement preference was set to full screen for the screenshot launches and restored afterwards.
- **Open:** click/hover QA; owner and tier thresholds to be confirmed.

## Acceptance checklist (running)

| Item | Result |
|------|--------|
| PM docs present | Pass |
| Dataset inventory vs real headers | Pass |
| Profile reproducible script | Pass (artefact present; re-run after env setup) |
| Schema contract frozen | Pass (ADR-005) |
| Documentation suite for reproduce/understand | Pass (docs index in README) |
| Docker Postgres up | Fail |
| Raw load row-count tests | Fail (loader missing; ingestion unit tests not Verified here) |
| Staging/analytics transform execution | Fail (SQL present, not run here) |
| Power BI connected demo | Fail |
| Secrets absent from Git | Pass (`.env` gitignored; `.env.example` placeholders only) |
| Raw CSVs not committed | Pass (`data/raw/**` gitignored) |
