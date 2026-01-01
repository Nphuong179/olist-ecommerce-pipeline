{{ config(materialized='view') }}

SELECT 
    TRIM(review_id) AS review_id,
    TRIM(order_id) AS order_id,
    review_score AS review_score,
    TRIM(review_comment_title) AS review_title,
    TRIM(review_comment_message) AS review_message,
    review_creation_date::TIMESTAMP AS review_created_timestamp,
    review_answer_timestamp::TIMESTAMP AS review_answer_timestamp

FROM {{ source("raw", "raw_order_reviews") }}