let
    Source = fn_AnalyticsTable("dim_customers"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"customer_key", Int64.Type},
            {"customer_unique_id", type text},
            {"geography_key", Int64.Type},
            {"zip_code_prefix", type text},
            {"city", type text},
            {"state", type text},
            {"first_order_date", type date},
            {"last_order_date", type date},
            {"order_count", Int64.Type},
            {"is_repeat_customer", type logical}
        }
    )
in
    Typed
