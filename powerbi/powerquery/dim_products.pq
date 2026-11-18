let
    Source = fn_AnalyticsTable("dim_products"),
    ReplaceNullCategory = Table.ReplaceValue(
        Source,
        null,
        "Unmapped",
        Replacer.ReplaceValue,
        {"product_category_name_english"}
    ),
    Typed = Table.TransformColumnTypes(
        ReplaceNullCategory,
        {
            {"product_key", Int64.Type},
            {"product_id", type text},
            {"product_category_name", type text},
            {"product_category_name_english", type text},
            {"product_name_length", Int64.Type},
            {"product_description_length", Int64.Type},
            {"product_photos_qty", Int64.Type},
            {"product_weight_g", type number},
            {"product_length_cm", type number},
            {"product_height_cm", type number},
            {"product_width_cm", type number}
        }
    )
in
    Typed
