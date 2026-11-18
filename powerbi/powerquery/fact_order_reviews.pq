let
    Source = fn_AnalyticsTable("fact_order_reviews"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"review_key", Int64.Type},
            {"review_id", type text},
            {"order_id", type text},
            {"order_key", Int64.Type},
            {"customer_key", Int64.Type},
            {"purchase_date_key", Int64.Type},
            {"review_creation_date_key", Int64.Type},
            {"review_score", Int64.Type},
            {"has_comment", type logical},
            {"review_comment_title", type text},
            {"review_comment_message", type text},
            {"review_answer_timestamp", type datetime}
        }
    ),
    // Exclude long text from model by default to keep Import lean (optional)
    RemoveHeavyText = Table.RemoveColumns(Typed, {"review_comment_title", "review_comment_message"}, MissingField.Ignore)
in
    RemoveHeavyText
