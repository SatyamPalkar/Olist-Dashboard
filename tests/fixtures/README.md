# Documented test fixtures

Synthetic mini-datasets for **unit** tests. Values are intentional, not copied
from production Olist rows.

| Scenario | Orders / rows | Purpose |
|----------|---------------|---------|
| Multi-item order `ord_a` | 2 items, 2 payments, 2 reviews | Fan-out / double-count |
| Late delivery `ord_b` | delivered after estimate | `is_late_delivery` |
| Canceled `ord_c` | no items | Missing-item handling |
| Duplicate `review_id` `rev_dup` | two rows | Surrogate-key necessity |

Do not treat fixture totals as production KPI baselines.
