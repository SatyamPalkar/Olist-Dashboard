let
    Source = fn_AnalyticsTable("fact_orders"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"order_key", Int64.Type},
            {"order_id", type text},
            {"customer_key", Int64.Type},
            {"customer_geography_key", Int64.Type},
            {"purchase_date_key", Int64.Type},
            {"approved_date_key", Int64.Type},
            {"delivered_customer_date_key", Int64.Type},
            {"estimated_delivery_date_key", Int64.Type},
            {"order_status", type text},
            {"is_delivered", type logical},
            {"is_canceled", type logical},
            {"merchandise_sales", type number},
            {"freight_charges", type number},
            {"order_value", type number},
            {"payment_amount", type number},
            {"item_count", Int64.Type},
            {"payment_count", Int64.Type},
            {"delivery_days", type number},
            {"is_late_delivery", type logical},
            {"review_score", Int64.Type}
        }
    )
in
    Typed
