{{ config(materialized='view') }}

SELECT 
    TRIM(review_id) AS review_id,
    TRIM(order_id) AS order_id,
    review_score AS review_score,
    TRIM(review_comment_title) AS review_title,
    TRIM(review_comment_message) AS review_message,
    CAST(review_creation_date AS TIMESTAMP) AS review_created_timestamp,
    CAST(review_answer_timestamp AS TIMESTAMP) AS review_answer_timestamp

FROM {{ source("raw", "order_reviews") }}