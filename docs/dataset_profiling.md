# Dataset profiling

**Status:** Verified (artefacts produced from local `data/raw/` CSVs)  
**Script:** `scripts/profile_olist_csvs.py`  
**Full report:** [`data_profile.md`](data_profile.md)  
**Machine-readable:** [`data_profile_raw.json`](data_profile_raw.json)  
**Related ADR:** ADR-006 in [`decisions.md`](decisions.md)

---

## Purpose

Profile the nine Olist source files before warehouse design and ETL so grain, keys, nulls, orphans, and date ranges are evidence-based — not assumed.

---

## How to reproduce

```bash
# From repo root, with CSVs in data/raw/ and dependencies installed
python scripts/profile_olist_csvs.py
```

Lightweight discovery alternative:

```bash
python scripts/discover_olist.py
# → docs/data_discovery.json
```

---

## Inventory (profile run)

| File | Rows (excl. header) | Columns | Notes |
|------|--------------------:|--------:|-------|
| `olist_customers_dataset.csv` | 99,441 | 5 | `customer_id` unique; `customer_unique_id` not unique |
| `olist_geolocation_dataset.csv` | 1,000,163 | 5 | ~261,831 full-row duplicates |
| `olist_order_items_dataset.csv` | 112,650 | 7 | Item→product orphans: 0 |
| `olist_order_payments_dataset.csv` | 103,886 | 5 | Multiple sequentials per order |
| `olist_order_reviews_dataset.csv` | 99,224 | 7 | `review_id` **not** unique (814 dup rows) |
| `olist_orders_dataset.csv` | 99,441 | 8 | Purchase timestamps ≈ 2016-09-04 → 2018-10-17 |
| `olist_products_dataset.csv` | 32,951 | 9 | Source spellings `*_lenght` retained in raw |
| `olist_sellers_dataset.csv` | 3,095 | 4 | — |
| `product_category_name_translation.csv` | 71 | 2 | PT → EN |

---

## Design-critical findings

| Finding | Implication |
|---------|-------------|
| Geolocation multi-row / zip + duplicates | Staging collapses to **one row per zip prefix** (AVG lat/lng) |
| `review_id` not unique; 547 orders with multiple reviews | Staging uses surrogate `review_sk`; keep all review rows unless BA signs off otherwise |
| ~158 customer zip prefixes missing from geolocation | Geography joins may leave orphans; do not invent coordinates |
| `customer_id` is order-scoped | Analytics customer dim keys on `customer_unique_id` |
| Item→product orphans = 0 | Safe FK from items to products at source |

---

## Status legend for consumers

| Consumer | How to use this profile |
|----------|-------------------------|
| Data Engineer | Row-count smoke tests must match these counts after load |
| SQL Architect | Grain and surrogate-key decisions already encoded in `database/` |
| QA | Assert geo collapse, review multiplicity, zip orphan behaviour |
| BI / BA | Do not invent columns; treat revenue ≠ profit |

---

## Gaps

- Profiling is **filesystem CSV only** — not a post-load warehouse profile.
- Re-run after any raw file replacement; refresh `data_profile.md` before changing contracts.
