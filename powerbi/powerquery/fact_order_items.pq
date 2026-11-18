let
    Source = fn_AnalyticsTable("fact_order_items"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"order_item_key", Int64.Type},
            {"order_id", type text},
            {"order_item_id", Int64.Type},
            {"order_key", Int64.Type},
            {"product_key", Int64.Type},
            {"seller_key", Int64.Type},
            {"customer_key", Int64.Type},
            {"purchase_date_key", Int64.Type},
            {"customer_geography_key", Int64.Type},
            {"seller_geography_key", Int64.Type},
            {"shipping_limit_date", type datetime},
            {"price", type number},
            {"freight_value", type number},
            {"item_total", type number}
        }
    )
in
    Typed
