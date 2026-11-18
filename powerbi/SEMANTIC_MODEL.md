# Semantic model — star schema in Power BI

Source DDL: `database/schemas/03_analytics_tables.sql`  
Mode: **Import** · Filter direction: **single** (dimension → fact) unless noted.

---

## 1. Tables in the model

### Dimensions

| Table | Grain | Date/key for relationships |
|-------|-------|----------------------------|
| `dim_date` | One calendar day | `date_key` (YYYYMMDD), `full_date` |
| `dim_geography` | One zip prefix | `geography_key` |
| `dim_customers` | One `customer_unique_id` | `customer_key` |
| `dim_products` | One `product_id` | `product_key` |
| `dim_sellers` | One `seller_id` | `seller_key` |

### Facts

| Table | Grain | Primary use |
|-------|-------|-------------|
| `fact_orders` | One order | Executive KPIs, delivery, geo demand |
| `fact_order_items` | One order line | Product / category / seller revenue |
| `fact_payments` | One payment sequence | Payment mix |
| `fact_order_reviews` | One review row | Satisfaction |

### Utility

| Table | Purpose |
|-------|---------|
| `_Measures` | Empty calculated table hosting all DAX measures |

---

## 2. Relationships (configure in Model view)

All relationships: **Many (`*`) → One (1)**, **single direction**, **active** unless stated.

### From `fact_orders`

| From | To | Active |
|------|-----|--------|
| `fact_orders[purchase_date_key]` | `dim_date[date_key]` | Yes — **primary date spine** |
| `fact_orders[customer_key]` | `dim_customers[customer_key]` | Yes |
| `fact_orders[customer_geography_key]` | `dim_geography[geography_key]` | Yes |

Optional inactive (role-playing dates — use `USERELATIONSHIP` in measures if needed):

| From | To |
|------|-----|
| `fact_orders[delivered_customer_date_key]` | `dim_date[date_key]` |
| `fact_orders[estimated_delivery_date_key]` | `dim_date[date_key]` |
| `fact_orders[approved_date_key]` | `dim_date[date_key]` |

### From `fact_order_items`

| From | To | Active |
|------|-----|--------|
| `fact_order_items[purchase_date_key]` | `dim_date[date_key]` | Yes |
| `fact_order_items[product_key]` | `dim_products[product_key]` | Yes |
| `fact_order_items[seller_key]` | `dim_sellers[seller_key]` | Yes |
| `fact_order_items[customer_key]` | `dim_customers[customer_key]` | Yes |
| `fact_order_items[customer_geography_key]` | `dim_geography[geography_key]` | Yes (may conflict if both facts filter geo — prefer **orders** for customer geo slicers; leave seller geo inactive or via `dim_sellers`) |

**Seller geography:** prefer `dim_sellers[geography_key]` → `dim_geography` (already in DDL) rather than dual paths from the item fact.

### From `fact_payments`

| From | To |
|------|-----|
| `fact_payments[purchase_date_key]` | `dim_date[date_key]` |
| `fact_payments[customer_key]` | `dim_customers[customer_key]` |

### From `fact_order_reviews`

| From | To |
|------|-----|
| `fact_order_reviews[purchase_date_key]` | `dim_date[date_key]` |
| `fact_order_reviews[customer_key]` | `dim_customers[customer_key]` |

### Dimension snowflake (optional)

| From | To | Notes |
|------|-----|-------|
| `dim_customers[geography_key]` | `dim_geography[geography_key]` | OK; keep single direction |
| `dim_sellers[geography_key]` | `dim_geography[geography_key]` | OK |

### Avoid

- **Fact-to-fact** active relationships (`fact_order_items[order_key]` → `fact_orders`) — causes ambiguous paths and double counting. Use shared dimensions; drill-through via `order_id` fields if needed.
- Bidirectional filtering — not required; creates unexpected filter propagation across facts.
- Many-to-many without a bridge — not present in this schema.

---

## 3. Date table configuration

1. Mark **`dim_date`** as the date table → column **`full_date`**.
2. Sort `month_name` by `month`; sort `day_name` by `day_of_week`.
3. Hide surrogate keys used only for relationships (`*_key` on facts) from Report view after relationships are set (optional tidy).

---

## 4. Measure home & calculation groups

- Create `_Measures` = `DATATABLE("Visible", STRING, {{BLANK()}})` or `{BLANK()}` disconnected table; hide the column.
- Place all measures from `dax/measures.dax` in `_Measures`.
- Do **not** add calculated columns for KPI math already available as measures.
- Acceptable calculated columns: none required for MVP (SQL Architect pre-computes `delivery_days`, `is_late_delivery`, `is_repeat_customer`).

---

## 5. Which fact for which visual

| Analysis | Use |
|----------|-----|
| Total revenue, orders, AOV, delivery, regional demand | `fact_orders` (+ `dim_geography` / `dim_date` / `dim_customers`) |
| Category / product / seller rankings, freight by category | `fact_order_items` (+ `dim_products` / `dim_sellers`) |
| Payment method distribution | `fact_payments` |
| Review score distributions / satisfaction | `fact_order_reviews` |

**Rule:** never sum `fact_payments.payment_value` and `fact_order_items.price` on the same visual without understanding grain — they are different economic concepts (see DDL comments).

---

## 6. Row-level security (RLS)

**Decision: do not implement RLS for MVP.**

Justification: public Olist dataset; single management audience; no tenant or region-restricted logins in the portfolio demo. Revisit if the report is published with seller- or state-scoped AD groups.

---

## 7. Model diagram (logical)

```
                    dim_date
                       ▲
                       │ purchase_date_key
     ┌─────────────────┼─────────────────┐
     │                 │                 │
fact_orders    fact_order_items    fact_payments
fact_order_reviews
     │                 │
     ▼                 ▼
dim_customers    dim_products
     │           dim_sellers
     ▼                 │
dim_geography ◄────────┘
```
