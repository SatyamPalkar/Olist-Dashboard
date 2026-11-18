# Power Query (M) — analytics Import

## How to use

1. In Power BI Desktop create parameters listed in `parameters.pq` (Manage Parameters).
2. For each table: New Source → Blank Query → Advanced Editor → paste the matching `.pq` file body.
3. Rename the query to the table name (`dim_date`, `fact_orders`, …).
4. Confirm **Import** mode on each query (right-click → no DirectQuery indicator).

All queries read schema `analytics` only.

## Query load order (conceptual)

Parameters → dimensions → facts. Refresh order is managed by the model; no query folding dependency between facts.
