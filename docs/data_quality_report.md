# Data Quality Report

**Generated (UTC):** 2026-11-18T03:41:13.929972+00:00
**Overall status:** `PASS_WITH_EXCEPTIONS`
**Total records tested:** 1,550,922

## Summary

- Critical referential integrity OK: **True**
- Entities with nulls: 3
- Payment − order_value (BRL): 160628.98

## Business metrics (Python oracle)

| Metric | Value |
|--------|-------|
| Total orders | 99,441 |
| Merchandise revenue | 13,591,643.70 |
| Freight total | 2,256,599.44 |
| Order value (merch+freight) | 15,848,243.14 |
| Payment total | 16,008,872.12 |
| AOV | 159.3733 |
| Avg review (all rows) | 4.0864 |
| Avg review (1/order) | 4.0863 |
| On-time rate | 91.8876% |
| Late rate | 8.1124% |
| Avg delivery days | 12.56 |
| Repeat customer rate | 3.1188% |

## Referential integrity

- `items_orphan_orders`: 0
- `payments_orphan_orders`: 0
- `reviews_orphan_orders`: 0
- `orders_orphan_customers`: 0
- `items_orphan_products`: 0
- `items_orphan_sellers`: 0
- `products_unmapped_categories`: 13

## Known exceptions

- **KX-001** — review_id is not unique in source: `{"count": 814, "severity": "Use surrogate review_sk in staging/analytics"}`
- **KX-002** — payment_total ≠ merchandise + freight: `{"difference_brl": 160628.98, "tolerance_note": "Vouchers/splits/order gaps; not treated as load failure"}`
- **KX-003** — orders without order_items: `{"count": 775, "disposition": "Typically canceled/unavailable; retain in fact_orders"}`
- **KX-004** — products missing English category translation: `{"count": 13, "disposition": "Label unmapped explicitly; do not drop products"}`
- **KX-005** — geolocation many rows per zip prefix: `{"disposition": "Aggregate to centroid in staging.stg_geolocation"}`

## Double-counting probes

Naive joins of items→payments or items→reviews **inflate** merchandise sums.
Warehouse facts pre-aggregate before join (see `analytics.fact_orders`).

- Orders with multiple items: 9803
- Orders with multiple payments: 2961
- Orders with multiple reviews: 547
- Duplicate `review_id` rows: 814

See also `docs/known_data_limitations.md`.
