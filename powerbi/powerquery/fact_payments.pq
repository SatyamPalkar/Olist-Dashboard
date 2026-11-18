let
    Source = fn_AnalyticsTable("fact_payments"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"payment_key", Int64.Type},
            {"order_id", type text},
            {"payment_sequential", Int64.Type},
            {"order_key", Int64.Type},
            {"customer_key", Int64.Type},
            {"purchase_date_key", Int64.Type},
            {"payment_type", type text},
            {"payment_installments", Int64.Type},
            {"payment_value", type number}
        }
    )
in
    Typed
