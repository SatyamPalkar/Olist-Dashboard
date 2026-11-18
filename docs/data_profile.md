# Olist raw data profile (Phase 1)

**Ground truth:** files in `data/raw/`. Dtypes are provisional pandas inferences from sampling/full read. No columns, joins, or metrics invented beyond shared column names (plus provisional zip-prefix name links).

## 1. Inventory

| File | Size (bytes) | Rows (excl. header) | Columns |
|------|-------------:|--------------------:|--------:|
| `olist_customers_dataset.csv` | 8,562,270 | 99,441 | 5 |
| `olist_geolocation_dataset.csv` | 61,273,883 | 1,000,163 | 5 |
| `olist_order_items_dataset.csv` | 15,007,623 | 112,650 | 7 |
| `olist_order_payments_dataset.csv` | 5,647,783 | 103,886 | 5 |
| `olist_order_reviews_dataset.csv` | 14,451,670 | 99,224 | 7 |
| `olist_orders_dataset.csv` | 17,654,914 | 99,441 | 8 |
| `olist_products_dataset.csv` | 2,379,446 | 32,951 | 9 |
| `olist_sellers_dataset.csv` | 163,589 | 3,095 | 4 |
| `product_category_name_translation.csv` | 2,613 | 71 | 2 |

## 2. Per-file profiles

### `olist_customers_dataset.csv`

- Size: **8,562,270** bytes | Rows: **99,441** | Columns: **5** | Full-row duplicates: **0**

| # | Column | Inferred dtype (provisional) | pandas dtype | Null/empty | Null rate | Distinct |
|---|--------|------------------------------|--------------|-----------:|----------:|---------:|
| 1 | `customer_id` | object | `object` | 0 | 0.0000% | 99,441 |
| 2 | `customer_unique_id` | object | `object` | 0 | 0.0000% | 96,096 |
| 3 | `customer_zip_code_prefix` | int | `int64` | 0 | 0.0000% | 14,995 |
| 4 | `customer_city` | object | `object` | 0 | 0.0000% | 4,119 |
| 5 | `customer_state` | object | `object` | 0 | 0.0000% | 27 |

**Column order (exact):** `customer_id`, `customer_unique_id`, `customer_zip_code_prefix`, `customer_city`, `customer_state`

#### Primary-key candidacy / uniqueness

| Key | Unique count | Row count | Is unique? | Notes |
|-----|-------------:|----------:|:----------:|-------|
| `customer_id` | 99441 | 99441 | yes | — |
| `customer_unique_id` | 96096 | 99441 | no | — |
| `customer_zip_code_prefix` | 14995 | 99441 | no | dup_rows=84446 |

#### Categorical-looking columns (top ≤20)

**`customer_state`** — distinct: 27

| Value | Count |
|-------|------:|
| `SP` | 41,746 |
| `RJ` | 12,852 |
| `MG` | 11,635 |
| `RS` | 5,466 |
| `PR` | 5,045 |
| `SC` | 3,637 |
| `BA` | 3,380 |
| `DF` | 2,140 |
| `ES` | 2,033 |
| `GO` | 2,020 |
| `PE` | 1,652 |
| `CE` | 1,336 |
| `PA` | 975 |
| `MT` | 907 |
| `MA` | 747 |
| `MS` | 715 |
| `PB` | 536 |
| `PI` | 495 |
| `RN` | 485 |
| `AL` | 413 |

#### ID / key format samples (truncated, 2–3 values)

- `customer_id`: `06b8999e2fba1a1fbc88172c00ba8bc7`, `18955e83d337fd6b2def6b18a428ac77`, `4e7b3e00288586ebd08712fdd0374a03`
- `customer_unique_id`: `861eff4711a542e4b93843c6dd7febb0`, `290c77bc529b7ac935b93aa66c333dc3`, `060e732b5b29e8181a18229c7b0b2b5e`
- `customer_zip_code_prefix`: `14409`, `9790`, `1151`

### `olist_geolocation_dataset.csv`

- Size: **61,273,883** bytes | Rows: **1,000,163** | Columns: **5** | Full-row duplicates: **261,831**

| # | Column | Inferred dtype (provisional) | pandas dtype | Null/empty | Null rate | Distinct |
|---|--------|------------------------------|--------------|-----------:|----------:|---------:|
| 1 | `geolocation_zip_code_prefix` | int | `int64` | 0 | 0.0000% | 19,015 |
| 2 | `geolocation_lat` | float | `float64` | 0 | 0.0000% | 717,360 |
| 3 | `geolocation_lng` | float | `float64` | 0 | 0.0000% | 717,613 |
| 4 | `geolocation_city` | object | `object` | 0 | 0.0000% | 8,011 |
| 5 | `geolocation_state` | object | `object` | 0 | 0.0000% | 27 |

**Column order (exact):** `geolocation_zip_code_prefix`, `geolocation_lat`, `geolocation_lng`, `geolocation_city`, `geolocation_state`

#### Primary-key candidacy / uniqueness

| Key | Unique count | Row count | Is unique? | Notes |
|-----|-------------:|----------:|:----------:|-------|
| `geolocation_zip_code_prefix` | 19015 | 1000163 | no | dup_rows=981148 |
| `geolocation_zip_code_prefix|geolocation_lat|geolocation_lng` | 720154 | 1000163 | no | dup_rows=280009 |
| `geolocation_zip_code_prefix_multiplicity` | 19015 | 1000163 | n/a | unique_prefixes=19015; prefixes_with_multiple_rows=17972; max_rows_per_prefix=1146; mean_rows_per_prefix=52.6 |

#### Categorical-looking columns (top ≤20)

**`geolocation_state`** — distinct: 27

| Value | Count |
|-------|------:|
| `SP` | 404,268 |
| `MG` | 126,336 |
| `RJ` | 121,169 |
| `RS` | 61,851 |
| `PR` | 57,859 |
| `SC` | 38,328 |
| `BA` | 36,045 |
| `GO` | 20,139 |
| `ES` | 16,748 |
| `PE` | 16,432 |
| `DF` | 12,986 |
| `MT` | 12,031 |
| `CE` | 11,674 |
| `PA` | 10,853 |
| `MS` | 10,431 |
| `MA` | 7,853 |
| `PB` | 5,538 |
| `RN` | 5,041 |
| `PI` | 4,549 |
| `AL` | 4,183 |

#### ID / key format samples (truncated, 2–3 values)

- `geolocation_zip_code_prefix`: `1037`, `1046`, `1046`

### `olist_order_items_dataset.csv`

- Size: **15,007,623** bytes | Rows: **112,650** | Columns: **7** | Full-row duplicates: **0**

| # | Column | Inferred dtype (provisional) | pandas dtype | Null/empty | Null rate | Distinct |
|---|--------|------------------------------|--------------|-----------:|----------:|---------:|
| 1 | `order_id` | object | `object` | 0 | 0.0000% | 98,666 |
| 2 | `order_item_id` | int | `int64` | 0 | 0.0000% | 21 |
| 3 | `product_id` | object | `object` | 0 | 0.0000% | 32,951 |
| 4 | `seller_id` | object | `object` | 0 | 0.0000% | 3,095 |
| 5 | `shipping_limit_date` | datetime (provisional) | `object` | 0 | 0.0000% | 93,318 |
| 6 | `price` | float | `float64` | 0 | 0.0000% | 5,968 |
| 7 | `freight_value` | float | `float64` | 0 | 0.0000% | 7,010 |

**Column order (exact):** `order_id`, `order_item_id`, `product_id`, `seller_id`, `shipping_limit_date`, `price`, `freight_value`

#### Primary-key candidacy / uniqueness

| Key | Unique count | Row count | Is unique? | Notes |
|-----|-------------:|----------:|:----------:|-------|
| `order_id` | 98666 | 112650 | no | dup_rows=13984 |
| `order_item_id` | 21 | 112650 | no | dup_rows=112629 |
| `product_id` | 32951 | 112650 | no | dup_rows=79699 |
| `seller_id` | 3095 | 112650 | no | dup_rows=109555 |
| `order_id|order_item_id` | 112650 | 112650 | yes | — |

#### Timestamp columns

| Column | Min (parsed) | Max (parsed) | Parseable | Unparseable (non-null) |
|--------|--------------|--------------|----------:|-----------------------:|
| `shipping_limit_date` | 2016-09-19 00:15:34 | 2020-04-09 22:35:08 | 112,650 | 0 |

#### ID / key format samples (truncated, 2–3 values)

- `order_id`: `00010242fe8c5a6d1ba2dd792cb16214`, `00018f77f2f0320c557190d7a144bdd3`, `000229ec398224ef6ca0657da4fc703e`
- `order_item_id`: `1`, `1`, `1`
- `product_id`: `4244733e06e7ecb4970a6e2683c13e61`, `e5f2d52b802189ee658865ca93d83a8f`, `c777355d18b72b67abbeef9df44fd0fd`
- `seller_id`: `48436dade18ac8b2bce089ec2a041202`, `dd7ddc04e1b6c2c614352b383efe2d36`, `5b51032eddd242adc84c38acab88f23d`

### `olist_order_payments_dataset.csv`

- Size: **5,647,783** bytes | Rows: **103,886** | Columns: **5** | Full-row duplicates: **0**

| # | Column | Inferred dtype (provisional) | pandas dtype | Null/empty | Null rate | Distinct |
|---|--------|------------------------------|--------------|-----------:|----------:|---------:|
| 1 | `order_id` | object | `object` | 0 | 0.0000% | 99,440 |
| 2 | `payment_sequential` | int | `int64` | 0 | 0.0000% | 29 |
| 3 | `payment_type` | object | `object` | 0 | 0.0000% | 5 |
| 4 | `payment_installments` | int | `int64` | 0 | 0.0000% | 24 |
| 5 | `payment_value` | float | `float64` | 0 | 0.0000% | 29,077 |

**Column order (exact):** `order_id`, `payment_sequential`, `payment_type`, `payment_installments`, `payment_value`

#### Primary-key candidacy / uniqueness

| Key | Unique count | Row count | Is unique? | Notes |
|-----|-------------:|----------:|:----------:|-------|
| `order_id` | 99440 | 103886 | no | dup_rows=4446 |
| `order_id|payment_sequential` | 103886 | 103886 | yes | — |
| `order_id_as_key` | 99440 | 103886 | no | orders_with_multiple_payments=2961 |

#### Categorical-looking columns (top ≤20)

**`payment_sequential`** — distinct: 29

| Value | Count |
|-------|------:|
| `1` | 99,360 |
| `2` | 3,039 |
| `3` | 581 |
| `4` | 278 |
| `5` | 170 |
| `6` | 118 |
| `7` | 82 |
| `8` | 54 |
| `9` | 43 |
| `10` | 34 |
| `11` | 29 |
| `12` | 21 |
| `13` | 13 |
| `14` | 10 |
| `15` | 8 |
| `17` | 6 |
| `19` | 6 |
| `18` | 6 |
| `16` | 6 |
| `20` | 4 |

**`payment_type`** — distinct: 5

| Value | Count |
|-------|------:|
| `credit_card` | 76,795 |
| `boleto` | 19,784 |
| `voucher` | 5,775 |
| `debit_card` | 1,529 |
| `not_defined` | 3 |

**`payment_installments`** — distinct: 24

| Value | Count |
|-------|------:|
| `1` | 52,543 |
| `2` | 12,413 |
| `3` | 10,461 |
| `4` | 7,098 |
| `10` | 5,331 |
| `5` | 5,239 |
| `8` | 4,268 |
| `6` | 3,920 |
| `7` | 1,626 |
| `9` | 644 |
| `12` | 133 |
| `15` | 74 |
| `18` | 27 |
| `11` | 23 |
| `24` | 18 |
| `20` | 17 |
| `13` | 16 |
| `14` | 15 |
| `17` | 8 |
| `16` | 5 |

#### ID / key format samples (truncated, 2–3 values)

- `order_id`: `b81ef226f3fe1789b1e8b2acac839d17`, `a9810da82917af2d9aefd1278f1dcfa0`, `25e8ea4e93396b6fa0d3dd708e76c1bd`

### `olist_order_reviews_dataset.csv`

- Size: **14,451,670** bytes | Rows: **99,224** | Columns: **7** | Full-row duplicates: **0**

| # | Column | Inferred dtype (provisional) | pandas dtype | Null/empty | Null rate | Distinct |
|---|--------|------------------------------|--------------|-----------:|----------:|---------:|
| 1 | `review_id` | object | `object` | 0 | 0.0000% | 98,410 |
| 2 | `order_id` | object | `object` | 0 | 0.0000% | 98,673 |
| 3 | `review_score` | int | `int64` | 0 | 0.0000% | 5 |
| 4 | `review_comment_title` | object | `object` | 87,658 | 88.3435% | 4,527 |
| 5 | `review_comment_message` | object | `object` | 58,274 | 58.7297% | 36,159 |
| 6 | `review_creation_date` | datetime (provisional) | `object` | 0 | 0.0000% | 636 |
| 7 | `review_answer_timestamp` | datetime (provisional) | `object` | 0 | 0.0000% | 98,248 |

**Column order (exact):** `review_id`, `order_id`, `review_score`, `review_comment_title`, `review_comment_message`, `review_creation_date`, `review_answer_timestamp`

#### Primary-key candidacy / uniqueness

| Key | Unique count | Row count | Is unique? | Notes |
|-----|-------------:|----------:|:----------:|-------|
| `review_id` | 98410 | 99224 | no | dup_rows=814 |
| `order_id` | 98673 | 99224 | no | dup_rows=551 |
| `order_id_as_key` | 98673 | 99224 | no | orders_with_multiple_reviews=547 |
| `review_id_duplicate_detail` | 98410 | 99224 | no | review_ids_with_multiple_rows=789; review_ids_spanning_multiple_order_ids=789 |

#### Timestamp columns

| Column | Min (parsed) | Max (parsed) | Parseable | Unparseable (non-null) |
|--------|--------------|--------------|----------:|-----------------------:|
| `review_creation_date` | 2016-10-02 00:00:00 | 2018-08-31 00:00:00 | 99,224 | 0 |
| `review_answer_timestamp` | 2016-10-07 18:32:28 | 2018-10-29 12:27:35 | 99,224 | 0 |

#### Categorical-looking columns (top ≤20)

**`review_score`** — distinct: 5

| Value | Count |
|-------|------:|
| `5` | 57,328 |
| `4` | 19,142 |
| `1` | 11,424 |
| `3` | 8,179 |
| `2` | 3,151 |

#### ID / key format samples (truncated, 2–3 values)

- `review_id`: `7bc2406110b926393aa56f80a40eba40`, `80e641a11e56f04c1ad469d5645fdfde`, `228ce5500dc1d8e020d8d1322874b6f0`
- `order_id`: `73fc7af87114b39712e6da79b0a377eb`, `a548910a1c6147796b98fdf73dbeba33`, `f9e4b658b201a9f2ecdecbb34bed034b`

### `olist_orders_dataset.csv`

- Size: **17,654,914** bytes | Rows: **99,441** | Columns: **8** | Full-row duplicates: **0**

| # | Column | Inferred dtype (provisional) | pandas dtype | Null/empty | Null rate | Distinct |
|---|--------|------------------------------|--------------|-----------:|----------:|---------:|
| 1 | `order_id` | object | `object` | 0 | 0.0000% | 99,441 |
| 2 | `customer_id` | object | `object` | 0 | 0.0000% | 99,441 |
| 3 | `order_status` | object | `object` | 0 | 0.0000% | 8 |
| 4 | `order_purchase_timestamp` | datetime (provisional) | `object` | 0 | 0.0000% | 98,875 |
| 5 | `order_approved_at` | datetime (provisional) | `object` | 160 | 0.1609% | 90,733 |
| 6 | `order_delivered_carrier_date` | datetime (provisional) | `object` | 1,783 | 1.7930% | 81,018 |
| 7 | `order_delivered_customer_date` | datetime (provisional) | `object` | 2,965 | 2.9817% | 95,664 |
| 8 | `order_estimated_delivery_date` | datetime (provisional) | `object` | 0 | 0.0000% | 459 |

**Column order (exact):** `order_id`, `customer_id`, `order_status`, `order_purchase_timestamp`, `order_approved_at`, `order_delivered_carrier_date`, `order_delivered_customer_date`, `order_estimated_delivery_date`

#### Primary-key candidacy / uniqueness

| Key | Unique count | Row count | Is unique? | Notes |
|-----|-------------:|----------:|:----------:|-------|
| `order_id` | 99441 | 99441 | yes | — |
| `customer_id` | 99441 | 99441 | yes | — |

#### Timestamp columns

| Column | Min (parsed) | Max (parsed) | Parseable | Unparseable (non-null) |
|--------|--------------|--------------|----------:|-----------------------:|
| `order_purchase_timestamp` | 2016-09-04 21:15:19 | 2018-10-17 17:30:18 | 99,441 | 0 |
| `order_approved_at` | 2016-09-15 12:16:38 | 2018-09-03 17:40:06 | 99,281 | 0 |
| `order_delivered_carrier_date` | 2016-10-08 10:34:01 | 2018-09-11 19:48:28 | 97,658 | 0 |
| `order_delivered_customer_date` | 2016-10-11 13:46:32 | 2018-10-17 13:22:46 | 96,476 | 0 |
| `order_estimated_delivery_date` | 2016-09-30 00:00:00 | 2018-11-12 00:00:00 | 99,441 | 0 |

#### Categorical-looking columns (top ≤20)

**`order_status`** — distinct: 8

| Value | Count |
|-------|------:|
| `delivered` | 96,478 |
| `shipped` | 1,107 |
| `canceled` | 625 |
| `unavailable` | 609 |
| `invoiced` | 314 |
| `processing` | 301 |
| `created` | 5 |
| `approved` | 2 |

#### ID / key format samples (truncated, 2–3 values)

- `order_id`: `e481f51cbdc54678b7cc49136f2d6af7`, `53cdb2fc8bc7dce0b6741e2150273451`, `47770eb9100c2d0c44946d9cf07ec65d`
- `customer_id`: `9ef432eb6251297304e76186b10a928d`, `b0830fb4747a6c6d20dea0b8c802d7ef`, `41ce2a54c0b03bf3443c3d931a367089`

### `olist_products_dataset.csv`

- Size: **2,379,446** bytes | Rows: **32,951** | Columns: **9** | Full-row duplicates: **0**

| # | Column | Inferred dtype (provisional) | pandas dtype | Null/empty | Null rate | Distinct |
|---|--------|------------------------------|--------------|-----------:|----------:|---------:|
| 1 | `product_id` | object | `object` | 0 | 0.0000% | 32,951 |
| 2 | `product_category_name` | object | `object` | 610 | 1.8512% | 73 |
| 3 | `product_name_lenght` | float (nullable int-like) | `float64` | 610 | 1.8512% | 66 |
| 4 | `product_description_lenght` | float (nullable int-like) | `float64` | 610 | 1.8512% | 2,960 |
| 5 | `product_photos_qty` | float (nullable int-like) | `float64` | 610 | 1.8512% | 19 |
| 6 | `product_weight_g` | float (nullable int-like) | `float64` | 2 | 0.0061% | 2,204 |
| 7 | `product_length_cm` | float (nullable int-like) | `float64` | 2 | 0.0061% | 99 |
| 8 | `product_height_cm` | float (nullable int-like) | `float64` | 2 | 0.0061% | 102 |
| 9 | `product_width_cm` | float (nullable int-like) | `float64` | 2 | 0.0061% | 95 |

**Column order (exact):** `product_id`, `product_category_name`, `product_name_lenght`, `product_description_lenght`, `product_photos_qty`, `product_weight_g`, `product_length_cm`, `product_height_cm`, `product_width_cm`

#### Primary-key candidacy / uniqueness

| Key | Unique count | Row count | Is unique? | Notes |
|-----|-------------:|----------:|:----------:|-------|
| `product_id` | 32951 | 32951 | yes | — |
| `product_category_name` | 73 | 32951 | no | nulls=610 |

#### Categorical-looking columns (top ≤20)

**`product_category_name`** — distinct: 73

| Value | Count |
|-------|------:|
| `cama_mesa_banho` | 3,029 |
| `esporte_lazer` | 2,867 |
| `moveis_decoracao` | 2,657 |
| `beleza_saude` | 2,444 |
| `utilidades_domesticas` | 2,335 |
| `automotivo` | 1,900 |
| `informatica_acessorios` | 1,639 |
| `brinquedos` | 1,411 |
| `relogios_presentes` | 1,329 |
| `telefonia` | 1,134 |
| `bebes` | 919 |
| `perfumaria` | 868 |
| `papelaria` | 849 |
| `fashion_bolsas_e_acessorios` | 849 |
| `cool_stuff` | 789 |
| `ferramentas_jardim` | 753 |
| `pet_shop` | 719 |
| `(null/empty)` | 610 |
| `eletronicos` | 517 |
| `construcao_ferramentas_construcao` | 400 |

#### ID / key format samples (truncated, 2–3 values)

- `product_id`: `1e9e8ef04dbcff4541ed26657ea517e5`, `3aa071139cb16b67ca9e5dea641aaa2f`, `96bd76ec8810374ed1b65e291975717f`
- `product_category_name`: `perfumaria`, `artes`, `esporte_lazer`

### `olist_sellers_dataset.csv`

- Size: **163,589** bytes | Rows: **3,095** | Columns: **4** | Full-row duplicates: **0**

| # | Column | Inferred dtype (provisional) | pandas dtype | Null/empty | Null rate | Distinct |
|---|--------|------------------------------|--------------|-----------:|----------:|---------:|
| 1 | `seller_id` | object | `object` | 0 | 0.0000% | 3,095 |
| 2 | `seller_zip_code_prefix` | int | `int64` | 0 | 0.0000% | 2,246 |
| 3 | `seller_city` | object | `object` | 0 | 0.0000% | 611 |
| 4 | `seller_state` | object | `object` | 0 | 0.0000% | 23 |

**Column order (exact):** `seller_id`, `seller_zip_code_prefix`, `seller_city`, `seller_state`

#### Primary-key candidacy / uniqueness

| Key | Unique count | Row count | Is unique? | Notes |
|-----|-------------:|----------:|:----------:|-------|
| `seller_id` | 3095 | 3095 | yes | — |
| `seller_zip_code_prefix` | 2246 | 3095 | no | dup_rows=849 |

#### Categorical-looking columns (top ≤20)

**`seller_state`** — distinct: 23

| Value | Count |
|-------|------:|
| `SP` | 1,849 |
| `PR` | 349 |
| `MG` | 244 |
| `SC` | 190 |
| `RJ` | 171 |
| `RS` | 129 |
| `GO` | 40 |
| `DF` | 30 |
| `ES` | 23 |
| `BA` | 19 |
| `CE` | 13 |
| `PE` | 9 |
| `PB` | 6 |
| `MS` | 5 |
| `RN` | 5 |
| `MT` | 4 |
| `RO` | 2 |
| `SE` | 2 |
| `AC` | 1 |
| `PI` | 1 |

#### ID / key format samples (truncated, 2–3 values)

- `seller_id`: `3442f8959a84dea7ee197c632cb2df15`, `d1b65fc7debc3361ea86b5f14c68d2e2`, `ce3ad9de960102d0677a81f5d0bb7b2d`
- `seller_zip_code_prefix`: `13023`, `13844`, `20031`

### `product_category_name_translation.csv`

- Size: **2,613** bytes | Rows: **71** | Columns: **2** | Full-row duplicates: **0**

| # | Column | Inferred dtype (provisional) | pandas dtype | Null/empty | Null rate | Distinct |
|---|--------|------------------------------|--------------|-----------:|----------:|---------:|
| 1 | `product_category_name` | object | `object` | 0 | 0.0000% | 71 |
| 2 | `product_category_name_english` | object | `object` | 0 | 0.0000% | 71 |

**Column order (exact):** `product_category_name`, `product_category_name_english`

#### Primary-key candidacy / uniqueness

| Key | Unique count | Row count | Is unique? | Notes |
|-----|-------------:|----------:|:----------:|-------|
| `product_category_name` | 71 | 71 | yes | — |

#### Categorical-looking columns (top ≤20)

**`product_category_name`** — distinct: 71

| Value | Count |
|-------|------:|
| `beleza_saude` | 1 |
| `informatica_acessorios` | 1 |
| `automotivo` | 1 |
| `cama_mesa_banho` | 1 |
| `moveis_decoracao` | 1 |
| `esporte_lazer` | 1 |
| `perfumaria` | 1 |
| `utilidades_domesticas` | 1 |
| `telefonia` | 1 |
| `relogios_presentes` | 1 |
| `alimentos_bebidas` | 1 |
| `bebes` | 1 |
| `papelaria` | 1 |
| `tablets_impressao_imagem` | 1 |
| `brinquedos` | 1 |
| `telefonia_fixa` | 1 |
| `ferramentas_jardim` | 1 |
| `fashion_bolsas_e_acessorios` | 1 |
| `eletroportateis` | 1 |
| `consoles_games` | 1 |

**`product_category_name_english`** — distinct: 71

| Value | Count |
|-------|------:|
| `health_beauty` | 1 |
| `computers_accessories` | 1 |
| `auto` | 1 |
| `bed_bath_table` | 1 |
| `furniture_decor` | 1 |
| `sports_leisure` | 1 |
| `perfumery` | 1 |
| `housewares` | 1 |
| `telephony` | 1 |
| `watches_gifts` | 1 |
| `food_drink` | 1 |
| `baby` | 1 |
| `stationery` | 1 |
| `tablets_printing_image` | 1 |
| `toys` | 1 |
| `fixed_telephony` | 1 |
| `garden_tools` | 1 |
| `fashion_bags_accessories` | 1 |
| `small_appliances` | 1 |
| `consoles_games` | 1 |

#### ID / key format samples (truncated, 2–3 values)

- `product_category_name`: `beleza_saude`, `informatica_acessorios`, `automotivo`
- `product_category_name_english`: `health_beauty`, `computers_accessories`, `auto`

## 3. Cross-file key coverage

Only exact shared column names, plus provisional zip-prefix name links (`customer_zip_code_prefix` / `seller_zip_code_prefix` ↔ `geolocation_zip_code_prefix`). `exact_column_name` coverage = % of distinct **child** values found in parent. `exact_column_name_parent_not_in_child` coverage = % of distinct **parent** values found in child (orphans = parent keys with no child match).

| Link type | Mapping | Parent | Child | Distinct (from-side) | Matched | Unmatched | Coverage % |
|-----------|---------|--------|-------|---------------------:|--------:|----------:|-----------:|
| exact_column_name | `customer_id` | `olist_customers_dataset.csv` | `olist_orders_dataset.csv` | 99,441 | 99,441 | 0 | 100.0 |
| exact_column_name_parent_not_in_child | `customer_id` | `olist_customers_dataset.csv` | `olist_orders_dataset.csv` | 99,441 | 99,441 | 0 | 100.0 |
| exact_column_name | `order_id` | `olist_orders_dataset.csv` | `olist_order_items_dataset.csv` | 98,666 | 98,666 | 0 | 100.0 |
| exact_column_name | `order_id` | `olist_orders_dataset.csv` | `olist_order_payments_dataset.csv` | 99,440 | 99,440 | 0 | 100.0 |
| exact_column_name | `order_id` | `olist_orders_dataset.csv` | `olist_order_reviews_dataset.csv` | 98,673 | 98,673 | 0 | 100.0 |
| exact_column_name_parent_not_in_child | `order_id` | `olist_orders_dataset.csv` | `olist_order_items_dataset.csv` | 99,441 | 98,666 | 775 | 99.2206 |
| exact_column_name_parent_not_in_child | `order_id` | `olist_orders_dataset.csv` | `olist_order_payments_dataset.csv` | 99,441 | 99,440 | 1 | 99.999 |
| exact_column_name_parent_not_in_child | `order_id` | `olist_orders_dataset.csv` | `olist_order_reviews_dataset.csv` | 99,441 | 98,673 | 768 | 99.2277 |
| exact_column_name | `product_category_name` | `product_category_name_translation.csv` | `olist_products_dataset.csv` | 73 | 71 | 2 | 97.2603 |
| exact_column_name_parent_not_in_child | `product_category_name` | `product_category_name_translation.csv` | `olist_products_dataset.csv` | 71 | 71 | 0 | 100.0 |
| exact_column_name | `product_id` | `olist_products_dataset.csv` | `olist_order_items_dataset.csv` | 32,951 | 32,951 | 0 | 100.0 |
| exact_column_name_parent_not_in_child | `product_id` | `olist_products_dataset.csv` | `olist_order_items_dataset.csv` | 32,951 | 32,951 | 0 | 100.0 |
| exact_column_name | `seller_id` | `olist_sellers_dataset.csv` | `olist_order_items_dataset.csv` | 3,095 | 3,095 | 0 | 100.0 |
| exact_column_name_parent_not_in_child | `seller_id` | `olist_sellers_dataset.csv` | `olist_order_items_dataset.csv` | 3,095 | 3,095 | 0 | 100.0 |
| provisional_zip_prefix_name_link | `customer_zip_code_prefix → geolocation_zip_code_prefix` | `olist_geolocation_dataset.csv` | `olist_customers_dataset.csv` | 14,995 | 14,837 | 158 | 98.9463 |
| provisional_zip_prefix_name_link | `seller_zip_code_prefix → geolocation_zip_code_prefix` | `olist_geolocation_dataset.csv` | `olist_sellers_dataset.csv` | 2,246 | 2,238 | 8 | 99.6438 |

### Unmatched key samples (up to 5)

- [exact_column_name_parent_not_in_child] `olist_order_items_dataset.csv` ↔ `olist_orders_dataset.csv` (`order_id`): ['0010dedd556712d7bb69a19cb7bbd37a', '00a500bc03bc4ec968e574c2553bed4b', '00b1cb0320190ca0daa2c88b35206009', '00bca4adac549020c1273714d04d0208', '00d0ffd14774da775ac832ba8520510f']
- [exact_column_name_parent_not_in_child] `olist_order_payments_dataset.csv` ↔ `olist_orders_dataset.csv` (`order_id`): ['bfbd0f9bdef84302105ad712db648a6c']
- [exact_column_name_parent_not_in_child] `olist_order_reviews_dataset.csv` ↔ `olist_orders_dataset.csv` (`order_id`): ['00143d0f86d6fbd9f9b38ab440ac16f5', '00335b686d693c7d72deeb12f8e89227', '00a77f9cc25b05b2004752593d7b8888', '00aa423621f35a9ca6c6240f275b0640', '016754282c7690ebd6658f9f8e0a49bb']
- [exact_column_name] `olist_products_dataset.csv` ↔ `product_category_name_translation.csv` (`product_category_name`): ['pc_gamer', 'portateis_cozinha_e_preparadores_de_alimentos']
- [provisional_zip_prefix_name_link] `olist_customers_dataset.csv` ↔ `olist_geolocation_dataset.csv` (`customer_zip_code_prefix → geolocation_zip_code_prefix`): ['11547', '12332', '12770', '13307', '13529']
- [provisional_zip_prefix_name_link] `olist_sellers_dataset.csv` ↔ `olist_geolocation_dataset.csv` (`seller_zip_code_prefix → geolocation_zip_code_prefix`): ['2285', '37708', '71551', '72580', '73815']

## 4. Data-quality flags

| Severity | File | Issue | Evidence (summary) |
|----------|------|-------|--------------------|
| high | `olist_geolocation_dataset.csv` | Composite key candidate `geolocation_zip_code_prefix|geolocation_lat|geolocation_lng` is NOT unique | `{"unique_count": 720154, "row_count": 1000163, "is_unique": false, "duplicate_rows": 280009}` |
| medium | `olist_geolocation_dataset.csv` | Exact full-row duplicates present | `{"full_duplicate_rows": 261831}` |
| info | `olist_geolocation_dataset.csv` | Multiple geolocation rows per zip_code_prefix (not 1:1) | `{"unique_prefixes": 19015, "row_count": 1000163, "prefixes_with_multiple_rows": 17972, "max_rows_per_prefix": 1146, "mean_rows_per_prefix": 52.6}` |
| info | `olist_order_payments_dataset.csv` | Multiple payment rows per order_id (expected grain) | `{"unique_count": 99440, "row_count": 103886, "is_unique": false, "orders_with_multiple_payments": 2961}` |
| medium | `olist_order_reviews_dataset.csv` | Multiple review rows per order_id | `{"unique_count": 98673, "row_count": 99224, "is_unique": false, "orders_with_multiple_reviews": 547}` |
| high | `olist_order_reviews_dataset.csv` | Some duplicate review_id values span multiple distinct order_id values | `{"unique_count": 98410, "row_count": 99224, "is_unique": false, "review_ids_with_multiple_rows": 789, "review_ids_spanning_multiple_order_ids": 789}` |
| info | `olist_orders_dataset.csv` | Parent `order_id` values in `olist_orders_dataset.csv` have no match in `olist_order_items_dataset.csv` (775 distinct; parent→child coverage 99.2206%) | `{"parent_keys_missing_from_child": 775, "parent_distinct": 99441, "coverage_pct": 99.2206, "samples": ["0010dedd556712d7bb69a19cb7bbd37a", "00a500bc03bc4ec968e574c2553bed4b", "0...` |
| info | `olist_orders_dataset.csv` | Parent `order_id` values in `olist_orders_dataset.csv` have no match in `olist_order_payments_dataset.csv` (1 distinct; parent→child coverage 99.999%) | `{"parent_keys_missing_from_child": 1, "parent_distinct": 99441, "coverage_pct": 99.999, "samples": ["bfbd0f9bdef84302105ad712db648a6c"], "link_type": "exact_column_name_parent_n...` |
| info | `olist_orders_dataset.csv` | Parent `order_id` values in `olist_orders_dataset.csv` have no match in `olist_order_reviews_dataset.csv` (768 distinct; parent→child coverage 99.2277%) | `{"parent_keys_missing_from_child": 768, "parent_distinct": 99441, "coverage_pct": 99.2277, "samples": ["00143d0f86d6fbd9f9b38ab440ac16f5", "00335b686d693c7d72deeb12f8e89227", "0...` |
| medium | `olist_products_dataset.csv` | Child values for `product_category_name` not found in parent `product_category_name_translation.csv` (coverage 97.2603%) | `{"orphans": 2, "child_distinct": 73, "coverage_pct": 97.2603, "orphan_samples": ["pc_gamer", "portateis_cozinha_e_preparadores_de_alimentos"], "link_type": "exact_column_name"}` |
| info | `olist_customers_dataset.csv` | Provisional zip-prefix values for `customer_zip_code_prefix → geolocation_zip_code_prefix` not found in `olist_geolocation_dataset.csv` (coverage 98.9463%) | `{"orphans": 158, "child_distinct": 14995, "coverage_pct": 98.9463, "orphan_samples": ["11547", "12332", "12770", "13307", "13529"], "link_type": "provisional_zip_prefix_name_link"}` |
| info | `olist_sellers_dataset.csv` | Provisional zip-prefix values for `seller_zip_code_prefix → geolocation_zip_code_prefix` not found in `olist_geolocation_dataset.csv` (coverage 99.6438%) | `{"orphans": 8, "child_distinct": 2246, "coverage_pct": 99.6438, "orphan_samples": ["2285", "37708", "71551", "72580", "73815"], "link_type": "provisional_zip_prefix_name_link"}` |
| info | `olist_orders_dataset.csv` | Nullable/empty values in `order_approved_at` (160 / 99441, 0.16%) | `{"null_count": 160, "null_rate": 0.001609}` |
| info | `olist_orders_dataset.csv` | Nullable/empty values in `order_delivered_carrier_date` (1783 / 99441, 1.79%) | `{"null_count": 1783, "null_rate": 0.01793}` |
| info | `olist_orders_dataset.csv` | Nullable/empty values in `order_delivered_customer_date` (2965 / 99441, 2.98%) | `{"null_count": 2965, "null_rate": 0.029817}` |
| info | `olist_products_dataset.csv` | Nullable/empty values in `product_category_name` (610 / 32951, 1.85%) | `{"null_count": 610, "null_rate": 0.018512}` |

## 5. Assumptions

- Null/empty = pandas NA **or** blank/whitespace-only string after strip.
- Inferred dtypes are provisional from pandas `read_csv` + timestamp parse attempts on name-hinted columns; not a warehouse type contract.
- Parent file for exact shared columns (when present): `order_id`→orders, `customer_id`→customers, `product_id`→products, `seller_id`→sellers, `product_category_name`→category translation; otherwise lexicographic. Reverse parent∉child gaps are also reported.
- Zip-prefix links are **provisional name-based** candidates only (not confirmed FKs); geolocation is multi-row per prefix.
- Categorical top-N capped at 20; review comment bodies not dumped.
- Secondary schema scrape used only for orientation; all numbers come from CSV files.

## 6. Artifacts

- Report: `docs/data_profile.md`
- Machine-readable: `docs/data_profile_raw.json`
- Script: `scripts/profile_olist_csvs.py`
