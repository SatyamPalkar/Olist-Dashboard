# Limitations and assumptions

**Status:** Implemented (governance documentation)

---

## Assumptions

| ID | Assumption | Impact if wrong |
|----|------------|-----------------|
| A1 | The nine official Olist CSVs are complete and unchanged relative to the Kaggle extract used for profiling | Row counts, joins, and KPI baselines drift |
| A2 | `customer_unique_id` is the correct persistent person key | Repeat rate and customer counts misstated |
| A3 | Merchandise GMV = sum of item `price`; freight is separate; payments may differ | Confusing payment totals with sales |
| A4 | Commercial KPIs default to **delivered** orders in BA docs unless a visual states otherwise | Over/under-counting vs BI non-canceled filter |
| A5 | Geolocation collapsed to AVG lat/lng per zip is adequate for regional BI | Local precision loss; orphan zips lack coordinates |
| A6 | Keeping all review rows is preferred until BA/BI sign off on “latest only” | Score averages can be multi-reviewed-order sensitive |
| A7 | SCD Type 1 dims are sufficient for a static public snapshot | No historical attribute tracking |
| A8 | Import-mode Power BI is appropriate for demo scale | Would revisit for near-real-time / huge models |
| A9 | Full reload ETL is acceptable (no CDC) | Longer runtimes if data volume grew substantially |
| A10 | Marketing Funnel dataset remains out of scope (ADR-001) | No lead/MQL analysis |

---

## Quantified source exceptions

See also [`known_data_limitations.md`](known_data_limitations.md) and the QA snapshot [`data_quality_report.md`](data_quality_report.md) (CSV-level checks; statuses there are independent of warehouse execution).

Notable quantified items: non-unique `review_id`, payment totals ≠ merchandise+freight, orders without items, incomplete category EN map, geo multi-row/zip.

**Baseline caution:** `business_insights.md` uses **delivered-only** merchandise (~R$ 13.22M). `data_quality_report.md` Python oracle figures can include a broader order set (~R$ 13.59M merchandise) — always check the filter before comparing.

---

## Limitations

### Data content

- **No profit / COGS / commission** — revenue figures are sales or charged amounts only.
- **No inventory, traffic, or conversion** — cannot measure sell-through or true demand.
- **Identity resolution** depends on Olist’s `customer_unique_id` quality.
- **Category taxonomy** is seller/source-defined; English labels depend on the translation file.
- **Observation window** roughly 2016–2018; early sparse months distort MoM %; post-extract repurchase unknown.
- **Zip → geo coverage** incomplete (~158 customer prefix orphans in profile).
- **`review_id` not unique**; multiple reviews per some orders.

### Analytical

- Delivery–review relationships are **associations**, not proven causation.
- Offline BA results are from **CSV pandas** (`scripts/ba_analysis.py`), not a Verified warehouse run.
- BI DAX currently filters **non-canceled**; BA dictionary prefers **delivered-only** — unresolved pending Phase 7.
- State of customer ≠ full logistics path; cross-state shipping economics are simplified.

### Platform / delivery

- Docker Compose **not** in repo yet — local Postgres setup is manual.
- Python raw-load ETL **not** implemented — `\copy` / Planned loader.
- Power BI `.pbix` and screenshots **not** produced — specs only.
- Automated test suite **not Verified** in the documentation environment used for this pass.
- No production scheduler, gateway, or SLA monitoring stack.

---

## How to extend safely

1. Change shared contracts only via ADR (`decisions.md`).
2. Re-run profiling after any raw file replacement.
3. Recompute BA cache and update insights with the same delivered-order rules.
4. Mark features Verified only with evidence in `progress.md`.
