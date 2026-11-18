"""Reference transforms mirroring database/staging/*.sql.

Used as an independent oracle for transformation unit tests until/alongside
the Data Engineer ETL package. Rules must stay aligned with SQL Architect
staging scripts — do not invent business logic.
"""

from __future__ import annotations

import pandas as pd


def transform_orders(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["order_id"] = df["order_id"].astype(str).str.strip()
    df["customer_id"] = df["customer_id"].astype(str).str.strip()
    df["order_status"] = df["order_status"].astype(str).str.strip().str.lower()
    df["order_purchase_timestamp"] = pd.to_datetime(
        df["order_purchase_timestamp"], errors="coerce"
    )
    for col in (
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ):
        df[col] = pd.to_datetime(df[col], errors="coerce")

    df = df[
        df["order_id"].notna()
        & (df["order_id"] != "")
        & df["customer_id"].notna()
        & (df["customer_id"] != "")
        & df["order_purchase_timestamp"].notna()
    ].copy()

    df["purchase_date"] = df["order_purchase_timestamp"].dt.date
    df["is_delivered"] = df["order_status"] == "delivered"
    df["is_canceled"] = df["order_status"] == "canceled"
    df["delivery_days"] = (
        df["order_delivered_customer_date"] - df["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400.0
    mask_both = (
        df["order_delivered_customer_date"].notna()
        & df["order_estimated_delivery_date"].notna()
    )
    # Nullable boolean: null when either date missing (matches SQL CASE)
    late = pd.Series(pd.NA, index=df.index, dtype="boolean")
    late.loc[mask_both] = (
        df.loc[mask_both, "order_delivered_customer_date"]
        > df.loc[mask_both, "order_estimated_delivery_date"]
    )
    df["is_late_delivery"] = late
    return df.drop_duplicates(subset=["order_id"], keep="first")


def transform_order_items(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["order_id"] = df["order_id"].astype(str).str.strip()
    df["order_item_id"] = pd.to_numeric(df["order_item_id"], errors="coerce")
    df["product_id"] = df["product_id"].astype(str).str.strip()
    df["seller_id"] = df["seller_id"].astype(str).str.strip()
    df["shipping_limit_date"] = pd.to_datetime(df["shipping_limit_date"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["freight_value"] = pd.to_numeric(df["freight_value"], errors="coerce")
    df = df[
        df["order_id"].notna()
        & df["order_item_id"].notna()
        & df["product_id"].notna()
        & (df["product_id"] != "")
        & df["seller_id"].notna()
        & (df["seller_id"] != "")
        & df["price"].notna()
        & df["freight_value"].notna()
    ].copy()
    df["order_item_id"] = df["order_item_id"].astype(int)
    df["item_total"] = (df["price"] + df["freight_value"]).round(2)
    return df.drop_duplicates(subset=["order_id", "order_item_id"], keep="first")


def transform_payments(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["order_id"] = df["order_id"].astype(str).str.strip()
    df["payment_sequential"] = pd.to_numeric(df["payment_sequential"], errors="coerce")
    df["payment_type"] = df["payment_type"].astype(str).str.strip().str.lower()
    df["payment_installments"] = pd.to_numeric(
        df["payment_installments"], errors="coerce"
    )
    df["payment_value"] = pd.to_numeric(df["payment_value"], errors="coerce")
    df = df[
        df["order_id"].notna()
        & df["payment_sequential"].notna()
        & df["payment_type"].notna()
        & df["payment_installments"].notna()
        & df["payment_value"].notna()
    ].copy()
    df["payment_sequential"] = df["payment_sequential"].astype(int)
    df["payment_installments"] = df["payment_installments"].astype(int)
    return df.drop_duplicates(subset=["order_id", "payment_sequential"], keep="first")


def transform_reviews(raw: pd.DataFrame) -> pd.DataFrame:
    """Keep all review rows; do not collapse on review_id (not unique)."""
    df = raw.copy()
    df["review_id"] = df["review_id"].astype(str).str.strip()
    df["order_id"] = df["order_id"].astype(str).str.strip()
    df["review_score"] = pd.to_numeric(df["review_score"], errors="coerce")
    df["review_creation_date"] = pd.to_datetime(
        df["review_creation_date"], errors="coerce"
    )
    df["review_answer_timestamp"] = pd.to_datetime(
        df["review_answer_timestamp"], errors="coerce"
    )
    title = df["review_comment_title"].fillna("").astype(str).str.strip()
    message = df["review_comment_message"].fillna("").astype(str).str.strip()
    df["has_comment"] = (title != "") | (message != "")
    df = df[
        df["review_id"].notna()
        & (df["review_id"] != "")
        & df["order_id"].notna()
        & (df["order_id"] != "")
        & df["review_score"].between(1, 5)
    ].copy()
    df["review_score"] = df["review_score"].astype(int)
    return df.reset_index(drop=True)


def transform_geolocation(raw: pd.DataFrame) -> pd.DataFrame:
    """Aggregate many coords per zip → one row (avg lat/lng)."""
    df = raw.copy()
    df["zip_code_prefix"] = (
        df["geolocation_zip_code_prefix"].astype(str).str.strip()
    )
    df["geolocation_lat"] = pd.to_numeric(df["geolocation_lat"], errors="coerce")
    df["geolocation_lng"] = pd.to_numeric(df["geolocation_lng"], errors="coerce")
    df = df.dropna(subset=["zip_code_prefix", "geolocation_lat", "geolocation_lng"])
    agg = (
        df.groupby("zip_code_prefix", as_index=False)
        .agg(
            avg_lat=("geolocation_lat", "mean"),
            avg_lng=("geolocation_lng", "mean"),
            city=("geolocation_city", "first"),
            state=("geolocation_state", "first"),
            point_count=("geolocation_lat", "size"),
        )
    )
    return agg
