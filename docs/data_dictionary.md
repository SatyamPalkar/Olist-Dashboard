# Data dictionary

**Status:** Implemented (source + warehouse contracts documented)  
**Sources of truth:** [`dataset_inventory.md`](dataset_inventory.md), [`../database/docs/contracts_raw_staging.md`](../database/docs/contracts_raw_staging.md), [`../database/schemas/03_analytics_tables.sql`](../database/schemas/03_analytics_tables.sql)

This dictionary covers (1) filesystem / raw columns and (2) analytics star-schema fields used by BI. Staging mirrors typed versions of raw entities; see contracts for full staging grain.

---

## 1. Source files (filesystem / `raw.*`)

All `raw.*` columns are loaded as **TEXT** plus `_loaded_at TIMESTAMPTZ`. Spelling of source typos (`product_name_lenght`, `product_description_lenght`) is preserved in raw and corrected in staging/analytics.

### Orders — `olist_orders_dataset.csv` → `raw.olist_orders`

| Column | Meaning |
|--------|---------|
| `order_id` | Order natural key |
| `customer_id` | Order-scoped customer key (FK to customers file) |
| `order_status` | Lifecycle status (delivered, shipped, canceled, …) |
| `order_purchase_timestamp` | Purchase event time |
| `order_approved_at` | Approval time (nullable) |
| `order_delivered_carrier_date` | Carrier handoff (nullable) |
| `order_delivered_customer_date` | Customer delivery (nullable) |
| `order_estimated_delivery_date` | Promised delivery estimate |

### Order items — `olist_order_items_dataset.csv` → `raw.olist_order_items`

| Column | Meaning |
|--------|---------|
| `order_id` | FK → orders |
| `order_item_id` | Line sequence within order |
| `product_id` | FK → products |
| `seller_id` | FK → sellers |
| `shipping_limit_date` | Seller ship-by timestamp |
| `price` | Line merchandise amount (excl. freight) |
| `freight_value` | Line freight charged to customer |

### Payments — `olist_order_payments_dataset.csv` → `raw.olist_order_payments`

| Column | Meaning |
|--------|---------|
| `order_id` | FK → orders |
| `payment_sequential` | Payment sequence within order |
| `payment_type` | credit_card, boleto, voucher, debit_card, not_defined |
| `payment_installments` | Installment count |
| `payment_value` | Amount for this payment row |

### Reviews — `olist_order_reviews_dataset.csv` → `raw.olist_order_reviews`

| Column | Meaning |
|--------|---------|
| `review_id` | Review identifier (**not reliably unique**) |
| `order_id` | FK → orders |
| `review_score` | 1–5 score |
| `review_comment_title` | Optional title |
| `review_comment_message` | Optional body |
| `review_creation_date` | Review created |
| `review_answer_timestamp` | Seller/platform answer time |

### Customers — `olist_customers_dataset.csv` → `raw.olist_customers`

| Column | Meaning |
|--------|---------|
| `customer_id` | Unique per order |
| `customer_unique_id` | Persistent person/account key |
| `customer_zip_code_prefix` | Geo join key |
| `customer_city` | City label |
| `customer_state` | UF state code |

### Products — `olist_products_dataset.csv` → `raw.olist_products`

| Column | Meaning |
|--------|---------|
| `product_id` | Product key |
| `product_category_name` | Portuguese category (nullable) |
| `product_name_lenght` | Source spelling retained |
| `product_description_lenght` | Source spelling retained |
| `product_photos_qty` | Photo count |
| `product_weight_g` / `*_cm` | Physical attributes |

### Sellers — `olist_sellers_dataset.csv` → `raw.olist_sellers`

| Column | Meaning |
|--------|---------|
| `seller_id` | Seller key |
| `seller_zip_code_prefix` | Geo join key |
| `seller_city` / `seller_state` | Location labels |

### Geolocation — `olist_geolocation_dataset.csv` → `raw.olist_geolocation`

| Column | Meaning |
|--------|---------|
| `geolocation_zip_code_prefix` | Zip prefix (many rows per prefix) |
| `geolocation_lat` / `geolocation_lng` | Coordinates |
| `geolocation_city` / `geolocation_state` | Labels |

### Category translation — `product_category_name_translation.csv`

| Column | Meaning |
|--------|---------|
| `product_category_name` | Portuguese category |
| `product_category_name_english` | English label |

---

## 2. Analytics dimensions

### `analytics.dim_date`

| Column | Type | Description |
|--------|------|-------------|
| `date_key` | INTEGER PK | YYYYMMDD |
| `full_date` | DATE | Calendar date |
| `year`, `quarter`, `month` | SMALLINT | Calendar parts |
| `month_name`, `day_name` | TEXT | Labels |
| `year_month` | TEXT | YYYY-MM |
| `is_weekend` | BOOLEAN | Weekend flag |

**Grain:** one calendar day (seeded 2016-01-01–2018-12-31).

### `analytics.dim_geography`

| Column | Type | Description |
|--------|------|-------------|
| `geography_key` | BIGSERIAL PK | Surrogate |
| `zip_code_prefix` | TEXT UK | Natural key |
| `city`, `state`, `state_name`, `region` | TEXT | Location attributes |
| `latitude`, `longitude` | NUMERIC | Averaged from staging geo |

**Grain:** one zip_code_prefix.

### `analytics.dim_customers`

| Column | Type | Description |
|--------|------|-------------|
| `customer_key` | BIGSERIAL PK | Surrogate |
| `customer_unique_id` | TEXT UK | Persistent customer |
| `geography_key` | BIGINT FK | → dim_geography |
| `first_order_date`, `last_order_date` | DATE | Order span |
| `order_count` | INTEGER | Orders attributed |
| `is_repeat_customer` | BOOLEAN | order_count > 1 |

**Grain:** one `customer_unique_id` (SCD Type 1).

### `analytics.dim_products`

| Column | Type | Description |
|--------|------|-------------|
| `product_key` | BIGSERIAL PK | Surrogate |
| `product_id` | TEXT UK | Natural key |
| `product_category_name` | TEXT | Portuguese |
| `product_category_name_english` | TEXT | English |
| Physical attrs | various | Weight / dimensions / lengths |

**Grain:** one `product_id`.

### `analytics.dim_sellers`

| Column | Type | Description |
|--------|------|-------------|
| `seller_key` | BIGSERIAL PK | Surrogate |
| `seller_id` | TEXT UK | Natural key |
| `geography_key` | BIGINT FK | → dim_geography |
| `zip_code_prefix`, `city`, `state` | TEXT | Location |

**Grain:** one `seller_id`.

---

## 3. Analytics facts

### `analytics.fact_orders`

| Column | Description |
|--------|-------------|
| `order_key` | Surrogate PK |
| `order_id` | Natural UK |
| `customer_key` | FK → dim_customers |
| `customer_geography_key` | FK → dim_geography |
| `purchase_date_key` | FK → dim_date |
| `order_status`, `is_delivered`, `is_canceled` | Status flags |
| `merchandise_sales` | SUM(item price) |
| `freight_charges` | SUM(item freight) |
| `order_value` | merchandise + freight |
| `payment_amount` | SUM(payments) — may differ from order_value |
| `item_count`, `payment_count` | Counts |
| `delivery_days`, `is_late_delivery` | Logistics measures |
| `review_score` | Latest/primary review on order (if any) |

**Grain:** one order. **Not profit** — no COGS.

### `analytics.fact_order_items`

| Column | Description |
|--------|-------------|
| `order_item_key` | Surrogate PK |
| `order_id` + `order_item_id` | Natural composite UK |
| `order_key`, `product_key`, `seller_key`, `customer_key` | FKs |
| `purchase_date_key` | FK → dim_date |
| `price`, `freight_value`, `item_total` | Line measures |

**Grain:** one order line. Primary fact for category/seller revenue.

### `analytics.fact_payments`

| Column | Description |
|--------|-------------|
| `payment_key` | Surrogate PK |
| `order_id` + `payment_sequential` | Natural composite UK |
| `payment_type`, `payment_installments`, `payment_value` | Payment attributes |

**Grain:** one payment sequence row.

### `analytics.fact_order_reviews`

| Column | Description |
|--------|-------------|
| `review_key` | Surrogate PK |
| `review_id` | Source id (not unique alone) |
| `order_key`, `customer_key`, date keys | FKs |
| `review_score` | 1–5 (CHECK) |
| Comment / has_comment flags | As implemented in DDL |

**Grain:** one review instance (from staging `review_sk`).

---

## 4. Explicit non-fields

The following are **not** in the dataset and must not appear as invented measures:

- Cost of goods, marketplace commission, net margin / profit
- Customer demographics beyond city/state/zip
- Marketing funnel / lead data (excluded by ADR-001)
- Real-time inventory or impressions
