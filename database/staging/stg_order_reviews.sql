-- staging.stg_order_reviews
-- Technique: surrogate key (BIGSERIAL), CASE for has_comment
-- Assumption: source review_id is NOT reliably unique → do not use as PK.
BEGIN;

TRUNCATE staging.stg_order_reviews RESTART IDENTITY CASCADE;

INSERT INTO staging.stg_order_reviews (
    review_id,
    order_id,
    review_score,
    review_comment_title,
    review_comment_message,
    review_creation_date,
    review_answer_timestamp,
    has_comment
)
SELECT
    TRIM(r.review_id)                                                       AS review_id,
    TRIM(r.order_id)                                                        AS order_id,
    TRIM(r.review_score)::SMALLINT                                          AS review_score,
    NULLIF(TRIM(r.review_comment_title), '')                                AS review_comment_title,
    NULLIF(TRIM(r.review_comment_message), '')                              AS review_comment_message,
    NULLIF(TRIM(r.review_creation_date), '')::TIMESTAMP                     AS review_creation_date,
    NULLIF(TRIM(r.review_answer_timestamp), '')::TIMESTAMP                  AS review_answer_timestamp,
    CASE
        WHEN NULLIF(TRIM(r.review_comment_message), '') IS NOT NULL
          OR NULLIF(TRIM(r.review_comment_title), '') IS NOT NULL
        THEN TRUE
        ELSE FALSE
    END                                                                     AS has_comment
FROM raw.olist_order_reviews r
WHERE NULLIF(TRIM(r.review_id), '') IS NOT NULL
  AND NULLIF(TRIM(r.order_id), '') IS NOT NULL
  AND NULLIF(TRIM(r.review_score), '') IS NOT NULL
  AND TRIM(r.review_score)::SMALLINT BETWEEN 1 AND 5;

COMMIT;
