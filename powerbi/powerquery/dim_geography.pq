let
    Source = fn_AnalyticsTable("dim_geography"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"geography_key", Int64.Type},
            {"zip_code_prefix", type text},
            {"city", type text},
            {"state", type text},
            {"state_name", type text},
            {"region", type text},
            {"latitude", type number},
            {"longitude", type number}
        }
    )
in
    Typed
