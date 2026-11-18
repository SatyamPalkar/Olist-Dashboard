-- analytics.fact_order_reviews
-- Grain: one staging review_sk → review_key
BEGIN;

TRUNCATE analytics.fact_order_reviews RESTART IDENTITY CASCADE;

INSERT INTO analytics.fact_order_reviews (
    review_id,
    order_id,
    order_key,
    customer_key,
    purchase_date_key,
    review_creation_date_key,
    review_score,
    has_comment,
    review_comment_title,
    review_comment_message,
    review_answer_timestamp
)
SELECT
    r.review_id,
    r.order_id,
    fo.order_key,
    fo.customer_key,
    fo.purchase_date_key,
    CASE
        WHEN r.review_creation_date IS NOT NULL
        THEN TO_CHAR(r.review_creation_date::DATE, 'YYYYMMDD')::INTEGER
    END                                                     AS review_creation_date_key,
    r.review_score,
    r.has_comment,
    r.review_comment_title,
    r.review_comment_message,
    r.review_answer_timestamp
FROM staging.stg_order_reviews r
JOIN analytics.fact_orders fo
    ON fo.order_id = r.order_id;

COMMIT;
