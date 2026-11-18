# PostgreSQL connection & refresh

**Database (from `.env.example`):** `retail_bi`  
**Schema:** `analytics`  
**Host / port / user:** `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`

---

## 1. Import vs DirectQuery — recommendation

| Mode | How it works | Pros | Cons |
|------|--------------|------|------|
| **Import** | Power BI copies tables into the VertiPaq model on refresh | Fast visuals, full DAX, works offline for demos, Time Intelligence reliable | Data freshness = last refresh; model size grows with history |
| **DirectQuery** | Each visual issues SQL to PostgreSQL live | Always current; smaller PBIX | Slower; DAX/time-intel limits; demo fragile if DB down; connector constraints |

### Recommendation for this dataset: **Import mode**

**Why**

1. Olist history is finite (~100k orders, ~2016–2018) — comfortably fits Import.
2. Portfolio / management demos need snappy cross-filtering across five pages.
3. Required measures (MoM/YoY, repeat rate, delivery rates) are cleaner and fully supported in Import.
4. ADR-004 (proposed) already prefers Import for offline demo reliability — **BI Developer accepts Import as the project standard.**

**When to reconsider DirectQuery:** near-real-time ops dashboards on a growing production warehouse, or models too large for desktop memory. Neither applies here.

**Composite models:** not required for MVP. Stay single-mode Import.

---

## 2. Desktop connection steps

1. Open Power BI Desktop → **Get data** → **PostgreSQL database**.
2. Server: `localhost` (or `POSTGRES_HOST`) · Database: `retail_bi`.
3. Data Connectivity mode: **Import**.
4. Credentials: Database / Username / Password from `.env` (never commit).
5. Navigator → expand schema **`analytics`** → select:

   | Table |
   |-------|
   | `dim_date` |
   | `dim_geography` |
   | `dim_customers` |
   | `dim_products` |
   | `dim_sellers` |
   | `fact_orders` |
   | `fact_order_items` |
   | `fact_payments` |
   | `fact_order_reviews` |

6. Prefer **Transform data** and apply the M scripts in `powerquery/` (or paste Advanced Editor content) so typing/rename steps stay reproducible.
7. **Close & Apply**.
8. Optional smoke-test only: SQL Architect also published `analytics.vw_*` KPI views (`database/views/vw_reporting_kpis.sql`). The interactive model uses **base dims/facts**; views are for SQL validation parity, not a second semantic model.

### Native query (optional, Advanced Editor)

```powerquery
PostgreSQL.Database(
    #"PostgreSQL Host",
    #"PostgreSQL Database",
    [Query="SELECT * FROM analytics.fact_orders"]
)
```

Prefer table navigation over ad-hoc SQL unless a reporting view is published by SQL Architect. Folding is better with table/view sources.

---

## 3. Gateway & scheduled refresh

| Environment | Refresh approach |
|-------------|------------------|
| Local Desktop | **Home → Refresh**; or automate with `pbixrefresher` / Task Scheduler calling Desktop (demo only) |
| Power BI Service | Publish `.pbix` → workspace → Dataset settings → configure **On-premises data gateway** (if Postgres is local/private) → schedule daily/hourly |
| Docker Postgres on laptop | Gateway must reach the container host; for portfolio, Desktop Import refresh after ETL is enough |

### Refresh requirements (actual)

1. **Upstream:** ETL must finish loading `analytics` before refresh (order: raw → staging → marts/facts).
2. **Credentials:** stored in Desktop / gateway; rotate with `.env`, not in Git.
3. **Privacy levels:** set PostgreSQL source to **Organizational** consistently to avoid formula.firewall blocks between queries.
4. **Incremental refresh:** optional stretch; full Import refresh is acceptable given dataset size.
5. **Failure handling:** if refresh fails, check Postgres up (`pg_isready`), schema exists, and user has `SELECT` on `analytics`.

### Minimum grants for the BI login

```sql
GRANT USAGE ON SCHEMA analytics TO olist;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO olist;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT ON TABLES TO olist;
```

---

## 4. Connection parameters (Power Query)

Create these parameters (see `powerquery/parameters.pq`):

| Parameter | Sample value |
|-----------|--------------|
| `PostgreSQL Host` | `localhost` |
| `PostgreSQL Port` | `5432` (informational; connector uses host string) |
| `PostgreSQL Database` | `retail_bi` |
| `PostgreSQL Schema` | `analytics` |

Host string for connector: typically `localhost` (port via server `host:5432` if non-default — Desktop UI has separate port in some builds; use `localhost:5432` in Server box when needed).

---

## 5. What not to do

- Do not point the final dashboard at static CSV exports.
- Do not bind visuals to `raw.*` or `staging.*`.
- Do not embed passwords in M code or theme JSON.
