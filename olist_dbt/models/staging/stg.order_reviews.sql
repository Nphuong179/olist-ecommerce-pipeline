{{ config(materialized='view') }}

SELECT 
    trim("review_id") as review_id,
    trim("order_id") as order_id,
    "review_score" as review_score,
    trim("review_comment_title") as review_title,
    trim("review_comment_message") as review_message,
    "review_creation_date"::DATE as review_created_date,
    "review_answer_timestamp"::TIMESTAMP as review_answer_timestamp

FROM {{ source("raw", "raw_order_reviews") }}