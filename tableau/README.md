# Tableau dashboard (Olist)

`Olist Executive Dashboard.twbx` is a four-page, dark-theme Tableau workbook (each page 1440 × 840, Tableau Desktop 2026.3). It follows status → drivers → action. The workbook is **generated from code** (`build_tableau_workbook.py`, standard library only). It reads seven single-grain CSV extracts exported from the PostgreSQL warehouse by `export_tableau_data.sql`.

The decision brief, KPI contract, worksheet spec and full QA table are in [`docs/tableau_build_spec.md`](../docs/tableau_build_spec.md). Screenshots are in [`screenshots/`](screenshots/).

| Page | Question | Contents |
|---|---|---|
| **Executive Overview** | How are we doing vs last year? | KPI cards (value, Jan–Aug 2018 vs 2017 delta, sparkline), secondary metrics, sales and late-rate trends, review by delivery timing, top categories, top states, worst late states |
| **Delivery Diagnostics** | Where and when does lateness concentrate? | Region × month late-rate heatmap, state late rate vs volume (tier colours), category late rate and review, repeat rate by first-order delivery, credit-card instalments |
| **Seller & Fulfilment** | Is it seller dispatch or carrier transit? | Dispatch vs transit days for late and on-time orders (same scale), late rate when the seller misses the shipping limit, late rate by route and by seller state, seller exception list |
| **Action Queue** | Which states first, and how will we know? | State exception table ranked by excess late orders, with Priority/Watch/Monitor tiers. Selecting a state filters the monthly trend. Playbook: owner, action, trigger, success measure, next step |

* **Navigation:** sidebar buttons on every page (the active page is cyan). Sheet tabs also work.
* **Colour:** cyan = growth / on time / at or below network; pink = risk / late / Priority; amber = Watch.
* **Tooltips:** every chart has one, with units, period and volumes.
* **Filters:** there are no quick filters. Headlines describe fixed, stated populations. The single filter action affects only the Action Queue trend.

```
data/raw/*.csv ─► scripts/build_warehouse.py ─► PostgreSQL raw → staging → analytics
                                                     │
              tableau/export_tableau_data.sql ───────┘─► tableau/data/*.csv (7 extracts)
                                                                  │
                          tableau/build_tableau_workbook.py ──────┘─► Olist Executive Dashboard.twb / .twbx
```

## Files

| File | Purpose |
|------|---------|
| `Olist Executive Dashboard.twbx` | **Open this one.** Packaged workbook with its data. |
| `Olist Executive Dashboard.twb` | Same workbook, reading `tableau/data/` by absolute path (for development). |
| `export_tableau_data.sql` | Exports the grain-safe extracts, with the data-quality profile and exclusions written as comments. |
| `build_tableau_workbook.py` | Generates both workbook files. `--qa DIR` also writes copies that open on each page (used for screenshots). |
| `screenshots/*.png` | Full-canvas captures of the four pages. |
| `Olist Delivery Analytics - Tableau Public.twbx` | Tableau Public edition: the same workbook, with the data packaged as `.hyper` extracts, because Tableau Public doesn't accept live text-file connections. |
| `build_hyper_extracts.py` | Converts the CSV extracts into `.hyper` files (needs `pip install tableauhyperapi`) and checks row counts and numeric totals against the CSVs. |

### Extracts (one grain each; never joined in Tableau)

| Extract | Grain | Rows | Notes |
|---|---|---:|---|
| `orders.csv` | delivered order | 96,478 | Base fact for KPIs, trends, states, heatmap and action queue |
| `order_items.csv` | order line | 110,197 | Category sales and share |
| `order_categories.csv` | order × category | 97,276 | Category late rate and review, counted per order |
| `order_fulfilment.csv` | delivered order | 96,478 | Seller dispatch and carrier transit days, missed shipping limit |
| `order_sellers.csv` | order × seller | 97,819 | Routes, seller states, seller exception rank |
| `customers.csv` | unique customer | 93,358 | First-order outcome and repeat flag |
| `card_orders.csv` | delivered order with a credit-card payment | 74,302 | Instalment count and band |
| `payments.csv` | payment row | 100,756 | Not charted directly (payment mix is sidebar text) |

## Rebuild

```bash
# warehouse built (scripts/build_warehouse.py --rebuild) and reachable via PG* variables
export PGHOST=127.0.0.1 PGPORT=55439 PGDATABASE=olist_test   # example: local test cluster
psql -v ON_ERROR_STOP=1 -f tableau/export_tableau_data.sql   # run from the project root
python3 tableau/build_tableau_workbook.py

# Tableau Public edition (packaged .hyper extracts)
pip install tableauhyperapi
python3 tableau/build_hyper_extracts.py
python3 tableau/build_tableau_workbook.py --public
```

## Scope, definitions and data-quality decisions

* **Scope:** delivered orders only (`order_status = 'delivered'`, ADR-007): 96,478 orders purchased 15 Sep 2016 – 29 Aug 2018, BRL.
* **Merchandise sales** = item price excluding freight. **AOV** = (price + freight) ÷ delivered orders.
* **Late rate** = orders delivered after the estimated date ÷ orders with both dates (8 excluded). It is a ratio of sums.
* **Network late rate** = `{FIXED : SUM([is_late]) / COUNT([is_late])}` = 8.11%. It is not affected by the 300+ order filter.
* **Excess late orders** = late orders − orders × network late rate. Positive is worse than the network; across all states the values sum to zero.
* **Tiers** (states with 300+ orders):
  * Priority: 3+ pp above the network **and** 50+ excess late orders.
  * Watch: 1+ pp above the network.
  * Monitor: otherwise.
  * The thresholds are an assumption for the business to confirm.
* **Seller dispatch** = purchase → carrier hand-off. **Carrier transit** = hand-off → customer delivery, in days. Dispatch + transit equals delivery days exactly.
  * The hand-off date comes from `staging.stg_orders` (it is not in `analytics`).
  * Of 96,478 delivered orders, 197 are excluded from timing: 2 with no hand-off date, 8 with no delivery date, 165 with a hand-off before purchase, and 23 with a hand-off after delivery.
  * Dispatch starts at purchase, not approval, because 1,350 hand-offs are dated before approval.
* **Missed shipping limit** = hand-off later than the seller's `shipping_limit_date` (the latest across the relevant items).
* **Order × seller grain:** 1,275 orders (1.3%) have 2–5 sellers. Each appears once per seller with the order's late flag and review, because Olist records one hand-off per order. The network rate at this grain is 8.0%. The seller exception rank uses sellers with 100+ seller-orders (210 sellers).
* **Retention cohort:** unique customers whose first delivered order (earliest purchase, tie-break order_id) was before 1 Mar 2018, which gives 6+ months to reorder. Repeat = 2+ delivered orders.
* **Credit-card instalments:**
  * Order-level count = MAX instalments over the order's credit-card payment rows (282 orders have several card rows).
  * 2 orders with 0 instalments are excluded.
  * 2,182 card orders also use another payment type; AOV uses the whole order value.
  * Bands: 1, 2–3, 4–6, 7–10, 11+ (the 11+ band holds the 12–24 tail).

## Verification (2026-11-18)

**Status: generated → opened → validated.** Click and hover checks are **pending**. Full QA table: `docs/tableau_build_spec.md` §8.

| Check | Result |
|-------|--------|
| Extracts vs warehouse / independent Python | Merchandise sales R$13,221,498.11, identical at order, item, order × category and order × seller grain. New extracts: 0 mismatches against `orders.csv` on late flag, review and delivery days. Card instalments match an independent computation from `payments.csv` exactly (74,302 orders). |
| Schema validation on open | 0 errors (Tableau log `detailed-error-msg`) |
| Queries | 0 failing query batches; no `InvalidField` warnings |
| Mark counts (log `tuples`) | KPI cards 1 · sparklines and trends 20 · review by timing 6 · ranked lists 10 · heatmap 100 · state scatter 21 · categories 22 · retention 2 · instalments 5 · dispatch / transit / shipping limit 2 each · routes 27 · seller states 12 · sellers 15 · action table 21 · action trend 20 |
| Visual QA (full-canvas screenshots) | All four pages: no clipped labels or truncated headers, colours as specified, footers complete |
| Click / hover | **Pending**: filter action, navigation buttons, tooltips |

## Insights shown

| Page / chart | Finding (verified) |
|---|---|
| KPI cards | Jan–Aug 2018 vs 2017: sales +141% (R$2.99M → R$7.22M), orders +140%, late rate 4.2% → 9.4%, review 4.23 → 4.14 |
| Trends | Sales doubled within a year, peaked in Nov 2017 and were flat at R$0.84–0.98M a month from Mar 2018. Late rate peaked at 14.3% (Nov 2017), 16.0% (Feb 2018) and 21.4% (Mar 2018) |
| Review vs timing | 4.32 when 14+ days early vs 1.67–1.72 when 8+ days late (association) |
| Concentration | SP = 38.3% of sales; the top 10 categories = 62.4% |
| Heatmap | Mar 2018 was 19%+ late in every region (Northeast 36.3%, North 39.2%) |
| Categories vs states | The 22 categories with 1,000+ orders span 5.5–9.8% late; states with 300+ orders span 5.0–23.9% |
| Retention | Repeat rate 3.19% when the first order was late vs 4.04% when on time (4,266 vs 51,257 customers; association) |
| Instalments | 33.2% of card orders use 1 instalment, 29.8% 2–3, 21.2% 4–6, 15.4% 7–10, 0.4% 11+. AOV R$101 → R$182 → R$333 (1x, 4–6x, 7–10x). Review 4.22 → 4.08 and late rate 7.2% → 8.7% from 1x to 7–10x (association) |
| Dispatch vs transit | Late orders: 5.8 dispatch + 25.7 transit days; on time: 3.0 + 7.9. About 86% of the extra 20.6 days is transit |
| Shipping limit | 9.0% of orders were handed over after the limit; they were 24.4% late vs 6.5% (association) |
| Routes | SP → RJ: 15.4% late on 8,273 seller-orders, the largest excess of 412 routes |
| Action queue | Priority states RJ, BA, CE, MA, ES, AL hold 1,176 excess late orders and R$426.7K of late-order sales. RJ alone holds 663 (56%) |
