# Query Documentation

## Reporting views (`analytics.vw_*`)

| View | KPI | Techniques demonstrated |
|------|-----|-------------------------|
| `vw_sales_by_month` | 1 | JOIN, GROUP BY, date dim |
| `vw_revenue_by_category` | 2 | JOIN dims, aggregation |
| `vw_top_10_products` | 3 | CTE, RANK window |
| `vw_sales_by_geography` | 4 | LEFT JOIN geo, COALESCE |
| `vw_average_order_value` | 5 | AVG at correct grain |
| `vw_mom_growth` | 6 | LAG, running SUM window |
| `vw_payment_distribution` | 7 | Window % of total |
| `vw_avg_delivery_time` | 8 | AVG, PERCENTILE_CONT |
| `vw_late_delivery_pct` | 9 | FILTER aggregates, CASE logic upstream |
| `vw_customer_repeat_behaviour` | 10 | CTE, customer_unique_id |
| `vw_seller_performance` | 11 | RANK, DENSE_RANK |
| `vw_review_score_distribution` | 12 | Distribution + % |

Ad-hoc pack: `views/kpi_queries.sql`.

## Optimisation notes

1. Prefer `fact_orders` for order-grain money; prefer `fact_order_items` for product/seller.
2. Prefer `mv_monthly_sales` in Power BI monthly cards if refresh schedule allows.
3. Avoid joining payments to items.
4. After load, run `scripts/explain_analyze_samples.sql` and confirm index usage on large GROUP BYs.
5. Production reporting queries list explicit columns (views already do).

## SQLAlchemy compatibility

Table/column names are lowercase snake_case without reserved-word collisions. Reflect with:

```python
from sqlalchemy import create_engine, MetaData
engine = create_engine("postgresql+psycopg2://user:pass@localhost:5432/olist_dw")
md = MetaData(schema="analytics")
md.reflect(bind=engine)
```

Views are regular Postgres views and reflect as such.

## Build / refresh

```bash
# First time (after creating empty DB)
psql -d olist_dw -v ON_ERROR_STOP=1 -f database/scripts/00_run_all.sql
# Load CSVs into raw.*, then:
psql -d olist_dw -v ON_ERROR_STOP=1 -f database/scripts/01_refresh_analytics.sql
```
