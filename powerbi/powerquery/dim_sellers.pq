let
    Source = fn_AnalyticsTable("dim_sellers"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"seller_key", Int64.Type},
            {"seller_id", type text},
            {"geography_key", Int64.Type},
            {"zip_code_prefix", type text},
            {"city", type text},
            {"state", type text}
        }
    )
in
    Typed
