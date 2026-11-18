# KPI Definitions

**Purpose:** Single source of truth for dashboard metrics.  
**Commercial base filter:** `order_status = 'delivered'` unless noted.  
**Important:** Metrics below measure **sales / GMV / charged amounts**, not profit. Cost of goods, marketplace commissions, and net margin are **not** available in the source extracts.

**Analysis grain reference tables**

| Logical table | Source file |
|---|---|
| `customers` | `olist_customers_dataset.csv` |
| `orders` | `olist_orders_dataset.csv` |
| `order_items` | `olist_order_items_dataset.csv` |
| `order_payments` | `olist_order_payments_dataset.csv` |
| `order_reviews` | `olist_order_reviews_dataset.csv` |
| `products` | `olist_products_dataset.csv` |
| `category_translation` | `product_category_name_translation.csv` |
| `sellers` | `olist_sellers_dataset.csv` |

---

## 1. Commercial KPIs

### 1.1 Merchandise revenue

| Field | Detail |
|---|---|
| **Definition** | Sum of item `price` for items on delivered orders. |
| **Business meaning** | Value of goods sold (merchandise GMV), excluding freight. |
| **Not** | Profit, net revenue after commissions, or payment totals (payments can include freight and may split across rows). |
| **Grain** | Order item → aggregated to period / category / region as needed. |
| **Dimensions** | Purchase month, category, customer state. |

```sql
SELECT SUM(oi.price) AS merchandise_revenue
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered';
```

**Observed baseline (full delivered history):** R$ 13,221,498.11

---

### 1.2 Freight charges

| Field | Detail |
|---|---|
| **Definition** | Sum of item `freight_value` for items on delivered orders. |
| **Business meaning** | Freight charged to customers on delivered order lines. |
| **Not** | Carrier cost paid by the platform/seller (unknown). |

```sql
SELECT SUM(oi.freight_value) AS freight_charges
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered';
```

**Observed baseline:** R$ 2,202,965.54

---

### 1.3 Total order value (TOV)

| Field | Detail |
|---|---|
| **Definition** | Merchandise revenue + freight charges for delivered orders. |
| **Business meaning** | Total amount charged on items (goods + freight). |
| **Alternative** | `SUM(payment_value)` from payments can differ due to payment sequencing, vouchers, and cancelled/non-delivered orders — **dashboard standard is items-based TOV for delivered orders**. |

```sql
SELECT
  SUM(oi.price) + SUM(oi.freight_value) AS total_order_value
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered';
```

**Observed baseline:** R$ 15,424,463.65

---

### 1.4 Average order value (AOV)

| Field | Detail |
|---|---|
| **Definition** | Total order value ÷ count of distinct delivered orders that have at least one order item. |
| **Business meaning** | Typical basket size including freight. |
| **Variant** | Merchandise-only AOV = merchandise revenue ÷ distinct orders (document if used). |

```sql
SELECT
  (SUM(oi.price) + SUM(oi.freight_value))
    / COUNT(DISTINCT oi.order_id) AS average_order_value
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered';
```

**Observed baseline:** R$ 159.88

---

### 1.5 Monthly revenue growth (MoM %)

| Field | Detail |
|---|---|
| **Definition** | Period-over-period % change in **merchandise revenue** by purchase calendar month. |
| **Formula** | `(rev_m - rev_m-1) / rev_m-1 * 100` |
| **Caveat** | Suppress or flag months with very low order volume (e.g. 2016 ramp-up); extreme MoM % in sparse months is not actionable. |

```sql
WITH monthly AS (
  SELECT
    DATE_TRUNC('month', o.order_purchase_timestamp) AS year_month,
    SUM(oi.price) AS merchandise_revenue
  FROM order_items oi
  JOIN orders o ON o.order_id = oi.order_id
  WHERE o.order_status = 'delivered'
  GROUP BY 1
)
SELECT
  year_month,
  merchandise_revenue,
  100.0 * (merchandise_revenue
           - LAG(merchandise_revenue) OVER (ORDER BY year_month))
         / NULLIF(LAG(merchandise_revenue) OVER (ORDER BY year_month), 0)
    AS mom_growth_pct
FROM monthly
ORDER BY year_month;
```

---

## 2. Customer KPIs

### 2.1 Unique customers

| Field | Detail |
|---|---|
| **Definition** | Count of distinct `customer_unique_id` with at least one delivered order in the selected period. |
| **Business meaning** | Active delivered-order customer base. |

```sql
SELECT COUNT(DISTINCT c.customer_unique_id) AS unique_customers
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.order_status = 'delivered';
-- AND o.order_purchase_timestamp between :start and :end
```

**Observed baseline (full history):** 93,358

---

### 2.2 Repeat customer rate

| Field | Detail |
|---|---|
| **Definition** | Share of unique customers with **≥ 2** delivered orders. |
| **Business meaning** | Retention / repurchase incidence (not revenue-weighted loyalty). |

```sql
WITH cust_orders AS (
  SELECT
    c.customer_unique_id,
    COUNT(DISTINCT o.order_id) AS n_orders
  FROM orders o
  JOIN customers c ON c.customer_id = o.customer_id
  WHERE o.order_status = 'delivered'
  GROUP BY c.customer_unique_id
)
SELECT
  100.0 * SUM(CASE WHEN n_orders >= 2 THEN 1 ELSE 0 END)
        / COUNT(*) AS repeat_customer_rate_pct
FROM cust_orders;
```

**Observed baseline:** 3.00% (2,801 of 93,358)

---

### 2.3 Orders per customer

| Field | Detail |
|---|---|
| **Definition** | Average number of delivered orders per unique customer. |
| **Business meaning** | Purchase frequency. |

```sql
WITH cust_orders AS (
  SELECT
    c.customer_unique_id,
    COUNT(DISTINCT o.order_id) AS n_orders
  FROM orders o
  JOIN customers c ON c.customer_id = o.customer_id
  WHERE o.order_status = 'delivered'
  GROUP BY c.customer_unique_id
)
SELECT AVG(n_orders * 1.0) AS orders_per_customer
FROM cust_orders;
```

**Observed baseline:** 1.03

---

### 2.4 Average review score

| Field | Detail |
|---|---|
| **Definition** | Mean `review_score` for delivered orders that have reviews. If multiple reviews exist per order, average to one score per order first. |
| **Business meaning** | Overall post-purchase satisfaction signal. |

```sql
WITH order_review AS (
  SELECT order_id, AVG(review_score) AS review_score
  FROM order_reviews
  GROUP BY order_id
)
SELECT AVG(r.review_score) AS average_review_score
FROM orders o
JOIN order_review r ON r.order_id = o.order_id
WHERE o.order_status = 'delivered';
```

**Observed baseline:** 4.16 / 5

---

### 2.5 Customer value segments (supporting metric)

| Field | Detail |
|---|---|
| **Definition** | Quartiles of unique customers by lifetime merchandise revenue on delivered orders (`Low`, `Medium`, `High`, `Top`). |
| **Business meaning** | Identifies concentration of GMV in higher-spend customers. |
| **Note** | Quartile labels are relative to this dataset, not industry standards. |

---

## 3. Operational KPIs

### 3.1 Average delivery time

| Field | Detail |
|---|---|
| **Definition** | Mean calendar days from `order_purchase_timestamp` to `order_delivered_customer_date` for delivered orders with both timestamps. |
| **Unit** | Days |

```sql
SELECT
  AVG(
    EXTRACT(EPOCH FROM (
      o.order_delivered_customer_date - o.order_purchase_timestamp
    )) / 86400.0
  ) AS average_delivery_days
FROM orders o
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_purchase_timestamp IS NOT NULL;
```

**Observed baseline:** 12.56 days

---

### 3.2 Late delivery percentage

| Field | Detail |
|---|---|
| **Definition** | % of delivered orders where actual delivery is **after** the estimated delivery date. |
| **Late flag** | `order_delivered_customer_date > order_estimated_delivery_date` |

```sql
SELECT
  100.0 * AVG(
    CASE
      WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
      THEN 1 ELSE 0
    END
  ) AS late_delivery_pct
FROM orders o
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_estimated_delivery_date IS NOT NULL;
```

**Observed baseline:** 8.11%

---

### 3.3 Estimated versus actual delivery time

| Field | Detail |
|---|---|
| **Definition** | Mean of (`actual delivery` − `estimated delivery`) in days. |
| **Interpretation** | **Negative** = delivered earlier than promised on average; **positive** = later than promised on average. |
| **Companion metrics** | Average estimated lead time; average actual lead time. |

```sql
SELECT
  AVG(
    EXTRACT(EPOCH FROM (
      o.order_delivered_customer_date - o.order_estimated_delivery_date
    )) / 86400.0
  ) AS avg_actual_minus_estimated_days
FROM orders o
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_estimated_delivery_date IS NOT NULL;
```

**Observed baseline:** −11.18 days (on average delivered earlier than the estimate)

---

## 4. Product KPIs

### 4.1 Revenue by category

| Field | Detail |
|---|---|
| **Definition** | Sum of `price` for delivered order items, grouped by English category name (fallback to Portuguese / `unknown`). |

```sql
SELECT
  COALESCE(t.product_category_name_english, p.product_category_name, 'unknown')
    AS category,
  SUM(oi.price) AS merchandise_revenue
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN products p ON p.product_id = oi.product_id
LEFT JOIN category_translation t
  ON t.product_category_name = p.product_category_name
WHERE o.order_status = 'delivered'
GROUP BY 1
ORDER BY merchandise_revenue DESC;
```

---

### 4.2 Product order volume

| Field | Detail |
|---|---|
| **Definition** | Count of order items and/or distinct orders by category (or product). |
| **Dashboard default** | Items (`COUNT(*)`) and distinct orders (`COUNT(DISTINCT order_id)`). |

```sql
SELECT
  COALESCE(t.product_category_name_english, p.product_category_name, 'unknown')
    AS category,
  COUNT(*) AS order_items,
  COUNT(DISTINCT oi.order_id) AS orders
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN products p ON p.product_id = oi.product_id
LEFT JOIN category_translation t
  ON t.product_category_name = p.product_category_name
WHERE o.order_status = 'delivered'
GROUP BY 1;
```

---

### 4.3 Category contribution

| Field | Detail |
|---|---|
| **Definition** | Category merchandise revenue ÷ total merchandise revenue × 100. |

```sql
WITH cat AS (
  SELECT
    COALESCE(t.product_category_name_english, p.product_category_name, 'unknown')
      AS category,
    SUM(oi.price) AS merchandise_revenue
  FROM order_items oi
  JOIN orders o ON o.order_id = oi.order_id
  JOIN products p ON p.product_id = oi.product_id
  LEFT JOIN category_translation t
    ON t.product_category_name = p.product_category_name
  WHERE o.order_status = 'delivered'
  GROUP BY 1
)
SELECT
  category,
  merchandise_revenue,
  100.0 * merchandise_revenue / SUM(merchandise_revenue) OVER () AS revenue_share_pct
FROM cat
ORDER BY merchandise_revenue DESC;
```

---

### 4.4 Freight intensity by category (supporting)

| Field | Detail |
|---|---|
| **Definition** | `SUM(freight_value) / SUM(price)` and average freight per item by category. |
| **Business meaning** | Relative freight burden vs merchandise value — useful for pricing and assortment economics (still not profit). |

---

## 5. Analytical standards (metric governance)

1. **Do not label revenue as profit.** No margin KPI until cost data exists.  
2. **Prefer items-based commercial metrics** for merchandise/freight consistency.  
3. **State the filter** (delivered / date range) on every KPI tile.  
4. **Association ≠ causation** for delivery vs review analyses.  
5. **Flag low-volume segments** (categories/states/months) before ranking “worst” or “best”.  
6. **Document currency** as Brazilian Real (BRL) amounts from source `price` / `freight_value`.

---

## 6. Refresh & ownership

| Item | Proposal |
|---|---|
| Metric owner | Business Analyst / Analytics lead |
| Data owner | Data Engineering |
| Refresh | Daily warehouse load; monthly management pack |
| Change control | Any formula change requires update to this document and dashboard changelog |
