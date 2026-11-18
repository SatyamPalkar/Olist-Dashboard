# Dataset inventory — Olist Brazilian E-Commerce

**Source:** [Kaggle — Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)  
**Scope:** Core 9 CSV files only (Marketing Funnel excluded — ADR-001)  
**Rule:** Columns listed here are from the public Olist schema. Do not invent fields.  
**Local path:** `data/raw/` (gitignored; must be downloaded by the operator)

**Verification note:** Column lists and grains verified against files in `data/raw/` on 2026-11-18. Row counts and DQ evidence: `docs/data_profile.md` (Data Engineer). Gate summary: `docs/phase1_orchestrator_review.md`.

---

## File list

| # | Filename | Entity | Rows | Declared grain |
|---|----------|--------|-----:|----------------|
| 1 | `olist_orders_dataset.csv` | Orders | 99,441 | 1 row per `order_id` |
| 2 | `olist_order_items_dataset.csv` | Order items | 112,650 | 1 row per (`order_id`, `order_item_id`) |
| 3 | `olist_order_payments_dataset.csv` | Payments | 103,886 | 1+ rows per order (`payment_sequential`) |
| 4 | `olist_order_reviews_dataset.csv` | Reviews | 99,224 | Review records linked to `order_id` (`review_id` **not** unique) |
| 5 | `olist_customers_dataset.csv` | Customers (per order) | 99,441 | 1 row per `customer_id` (order-scoped) |
| 6 | `olist_products_dataset.csv` | Products | 32,951 | 1 row per `product_id` |
| 7 | `olist_sellers_dataset.csv` | Sellers | 3,095 | 1 row per `seller_id` |
| 8 | `olist_geolocation_dataset.csv` | Geolocation | 1,000,163 | Many rows per zip prefix |
| 9 | `product_category_name_translation.csv` | Category translation | 71 | 1 row per Portuguese category name |

---

## Columns

### `olist_orders_dataset.csv`

| Column | Role |
|--------|------|
| `order_id` | PK |
| `customer_id` | FK → customers |
| `order_status` | Attribute (e.g. delivered, shipped, canceled, …) |
| `order_purchase_timestamp` | Event time |
| `order_approved_at` | Event time (nullable) |
| `order_delivered_carrier_date` | Event time (nullable) |
| `order_delivered_customer_date` | Event time (nullable) |
| `order_estimated_delivery_date` | Attribute (nullable) |

### `olist_order_items_dataset.csv`

| Column | Role |
|--------|------|
| `order_id` | Composite PK / FK → orders |
| `order_item_id` | Composite PK (sequence within order) |
| `product_id` | FK → products |
| `seller_id` | FK → sellers |
| `shipping_limit_date` | Attribute |
| `price` | Measure (item price excl. freight) |
| `freight_value` | Measure |

### `olist_order_payments_dataset.csv`

| Column | Role |
|--------|------|
| `order_id` | FK → orders |
| `payment_sequential` | Sequence within order |
| `payment_type` | Attribute (`credit_card`, `boleto`, `voucher`, `debit_card`, `not_defined`) |
| `payment_installments` | Attribute |
| `payment_value` | Measure |

### `olist_order_reviews_dataset.csv`

| Column | Role |
|--------|------|
| `review_id` | ID (NOT unique in this dump — see profile) |
| `order_id` | FK → orders |
| `review_score` | Measure (1–5) |
| `review_comment_title` | Attribute (nullable) |
| `review_comment_message` | Attribute (nullable) |
| `review_creation_date` | Event time |
| `review_answer_timestamp` | Event time (nullable) |

### `olist_customers_dataset.csv`

| Column | Role |
|--------|------|
| `customer_id` | PK (unique per order) |
| `customer_unique_id` | Natural customer key across orders |
| `customer_zip_code_prefix` | Geo key → geolocation |
| `customer_city` | Attribute |
| `customer_state` | Attribute |

### `olist_products_dataset.csv`

| Column | Role |
|--------|------|
| `product_id` | PK |
| `product_category_name` | Attribute (Portuguese; nullable) |
| `product_name_lenght` | Attribute (source spelling retained) |
| `product_description_lenght` | Attribute (source spelling retained) |
| `product_photos_qty` | Attribute |
| `product_weight_g` | Attribute |
| `product_length_cm` | Attribute |
| `product_height_cm` | Attribute |
| `product_width_cm` | Attribute |

### `olist_sellers_dataset.csv`

| Column | Role |
|--------|------|
| `seller_id` | PK |
| `seller_zip_code_prefix` | Geo key → geolocation |
| `seller_city` | Attribute |
| `seller_state` | Attribute |

### `olist_geolocation_dataset.csv`

| Column | Role |
|--------|------|
| `geolocation_zip_code_prefix` | Zip prefix (not unique) |
| `geolocation_lat` | Coordinate |
| `geolocation_lng` | Coordinate |
| `geolocation_city` | Attribute |
| `geolocation_state` | Attribute |

### `product_category_name_translation.csv`

| Column | Role |
|--------|------|
| `product_category_name` | PK / FK to products category |
| `product_category_name_english` | Attribute |

---

## Join graph

```
customers.customer_id  ◄──── orders.customer_id
orders.order_id        ◄──── order_items.order_id
orders.order_id        ◄──── order_payments.order_id
orders.order_id        ◄──── order_reviews.order_id
order_items.product_id ────► products.product_id
order_items.seller_id  ────► sellers.seller_id
products.product_category_name ────► translation.product_category_name
customers.customer_zip_code_prefix ≈ geolocation.geolocation_zip_code_prefix
sellers.seller_zip_code_prefix     ≈ geolocation.geolocation_zip_code_prefix
```

**Caveats (validated in Phase 1 profiling — modelling ADRs still open):**

1. `customer_id` is order-scoped; use `customer_unique_id` for repeat-buyer analysis (not unique: 96,096 / 99,441).
2. An order may have multiple items and multiple sellers.
3. Payments may not be 1:1 with orders; sum `payment_value` carefully vs item `price` + `freight_value`.
4. Geolocation has many lat/lng rows per zip prefix (261,831 full-row duplicates) — aggregate before joining to facts.
5. Reviews: 768 orders have none; 547 orders have multiple rows; `review_id` can span multiple `order_id`s — grain TBD (ADR pending).
6. Product category name spelling quirks (`lenght`) are preserved from source.
7. 775 orders have no items; 1 order has no payment; 2 product categories lack English translation.

---

## Out of scope

- Olist Marketing Funnel dataset
- External economic / weather / holiday calendars (unless later ADR)
- NLP production models on review text (optional stretch; not required for MVP dashboard)
