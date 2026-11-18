let
    Source = fn_AnalyticsTable("dim_date"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"date_key", Int64.Type},
            {"full_date", type date},
            {"year", Int64.Type},
            {"quarter", Int64.Type},
            {"month", Int64.Type},
            {"month_name", type text},
            {"month_name_short", type text},
            {"day_of_month", Int64.Type},
            {"day_of_week", Int64.Type},
            {"day_name", type text},
            {"week_of_year", Int64.Type},
            {"year_month", type text},
            {"is_weekend", type logical}
        }
    )
in
    Typed
