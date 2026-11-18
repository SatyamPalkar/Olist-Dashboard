# Data acquisition

Olist CSVs are **not** stored in this repository.

## Steps

1. Create a Kaggle account and accept the dataset terms:  
   https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
2. Download the dataset (UI or [Kaggle API](https://github.com/Kaggle/kaggle-api)).
3. Extract so that these exact filenames exist under `data/raw/`:

```
olist_customers_dataset.csv
olist_geolocation_dataset.csv
olist_order_items_dataset.csv
olist_order_payments_dataset.csv
olist_order_reviews_dataset.csv
olist_orders_dataset.csv
olist_products_dataset.csv
olist_sellers_dataset.csv
product_category_name_translation.csv
```

4. Do not rename, overwrite, or “clean in place” files in `data/raw/`.

## Optional API sketch

```bash
# Requires ~/.kaggle/kaggle.json (never commit it)
pip install kaggle
kaggle datasets download -d olistbr/brazilian-ecommerce -p data/raw --unzip
```

## Acceptance

Phase 2 profiling may start only when all nine files are present and readable.
