# Raw & Staging Table Contracts

**Owner (raw load):** Data Engineer  
**Owner (staging transforms + analytics):** SQL Architect (Agent 2)  
**Source:** Olist Brazilian E-Commerce Public Dataset (Kaggle)

## Assumptions

1. Source files are the nine Olist CSVs (orders, order_items, order_payments, order_reviews, customers, products, sellers, geolocation, product_category_name_translation).
2. Raw columns are loaded as `TEXT` for resilience; typing happens in staging.
3. `customer_id` is **per order**; `customer_unique_id` is the persistent person key.
4. Source column spelling `product_name_lenght` / `product_description_lenght` is preserved in raw and corrected in staging.
5. `review_id` is **not** treated as a reliable unique key; staging assigns `review_sk`.
6. Geolocation has many points per zip; staging collapses to one row per `zip_code_prefix`.

---

## RAW contracts

| Raw table | Source file | Expected columns |
|-----------|-------------|------------------|
| `raw.olist_orders` | `olist_orders_dataset.csv` | order_id, customer_id, order_status, order_purchase_timestamp, order_approved_at, order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date |
| `raw.olist_order_items` | `olist_order_items_dataset.csv` | order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value |
| `raw.olist_order_payments` | `olist_order_payments_dataset.csv` | order_id, payment_sequential, payment_type, payment_installments, payment_value |
| `raw.olist_order_reviews` | `olist_order_reviews_dataset.csv` | review_id, order_id, review_score, review_comment_title, review_comment_message, review_creation_date, review_answer_timestamp |
| `raw.olist_customers` | `olist_customers_dataset.csv` | customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state |
| `raw.olist_products` | `olist_products_dataset.csv` | product_id, product_category_name, product_name_lenght, product_description_lenght, product_photos_qty, product_weight_g, product_length_cm, product_height_cm, product_width_cm |
| `raw.olist_sellers` | `olist_sellers_dataset.csv` | seller_id, seller_zip_code_prefix, seller_city, seller_state |
| `raw.olist_geolocation` | `olist_geolocation_dataset.csv` | geolocation_zip_code_prefix, geolocation_lat, geolocation_lng, geolocation_city, geolocation_state |
| `raw.product_category_name_translation` | `product_category_name_translation.csv` | product_category_name, product_category_name_english |

All raw tables also include `_loaded_at TIMESTAMPTZ DEFAULT NOW()`.

### Suggested load (Data Engineer)

```sql
\copy raw.olist_orders FROM 'data/olist_orders_dataset.csv' CSV HEADER
\copy raw.olist_order_items FROM 'data/olist_order_items_dataset.csv' CSV HEADER
\copy raw.olist_order_payments FROM 'data/olist_order_payments_dataset.csv' CSV HEADER
\copy raw.olist_order_reviews FROM 'data/olist_order_reviews_dataset.csv' CSV HEADER
\copy raw.olist_customers FROM 'data/olist_customers_dataset.csv' CSV HEADER
\copy raw.olist_products FROM 'data/olist_products_dataset.csv' CSV HEADER
\copy raw.olist_sellers FROM 'data/olist_sellers_dataset.csv' CSV HEADER
\copy raw.olist_geolocation FROM 'data/olist_geolocation_dataset.csv' CSV HEADER
\copy raw.product_category_name_translation FROM 'data/product_category_name_translation.csv' CSV HEADER
```

---

## STAGING contracts

| Staging table | Grain | PK | Notes |
|---------------|-------|----|-------|
| `stg_orders` | 1 row / order_id | `order_id` | Typed timestamps; `purchase_date`; `delivery_days`; `is_late_delivery` |
| `stg_order_items` | order_id + order_item_id | composite | `price`, `freight_value`, `item_total` |
| `stg_order_payments` | order_id + payment_sequential | composite | Lowercased `payment_type` |
| `stg_order_reviews` | 1 row / review instance | `review_sk` | Score 1–5; `has_comment` |
| `stg_customers` | 1 row / customer_id | `customer_id` | Also carries `customer_unique_id` + geo |
| `stg_products` | 1 row / product_id | `product_id` | English category joined |
| `stg_sellers` | 1 row / seller_id | `seller_id` | Normalised city/state |
| `stg_geolocation` | 1 row / zip_code_prefix | `zip_code_prefix` | AVG lat/lng |
| `stg_product_category_translation` | 1 row / PT category | `product_category_name` | PT→EN map |

### Change control

Any column rename/type change in raw or staging requires joint sign-off between Data Engineer and SQL Architect before analytics marts are rebuilt.
