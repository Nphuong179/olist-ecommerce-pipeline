{{ config(materialized='table') }}

SELECT
    -- Natural key
    sor.review_id,

    -- Foreign key to orders
    sor.order_id,

    -- Foreign key to customer dimension
    dc.customer_key,

    -- Review scoring
    sor.review_score,

    CASE
        WHEN sor.review_score >= 4 THEN 'positive'
        WHEN sor.review_score = 3 THEN 'neutral'
        WHEN sor.review_score <= 2 THEN 'negative'
    END AS review_sentiment,

    -- Review contents
    sor.review_title,
    sor.review_message,
    LENGTH(sor.review_title) AS review_title_length,
    LENGTH(sor.review_message) AS review_message_length,

    -- Review timing
    sor.review_created_timestamp,
    sor.review_answer_timestamp,
    so.order_delivered_customer_timestamp,

    CASE
        WHEN so.order_delivered_customer_timestamp IS NOT NULL
            AND sor.review_created_timestamp IS NOT NULL
        THEN DATE_DIFF('day', so.order_delivered_customer_timestamp, sor.review_created_timestamp)
    END AS days_from_delivery_to_review,

    -- Derived metrics: Response behavior
    CASE
        WHEN sor.review_answer_timestamp IS NOT NULL
        THEN DATE_DIFF('hour', sor.review_created_timestamp, sor.review_answer_timestamp)
    END AS hours_to_seller_response,

    -- Derived flags: Response behavior
    CASE
        WHEN sor.review_answer_timestamp IS NOT NULL
        THEN TRUE
        ELSE FALSE
    END AS has_seller_response,

    CASE
        WHEN sor.review_answer_timestamp IS NOT NULL
            AND DATE_DIFF('hour', sor.review_created_timestamp, sor.review_answer_timestamp) <= 24
        THEN TRUE
        ELSE FALSE
    END AS is_fast_response,

    -- Derived flags: Review completeness
    CASE
        WHEN COUNT(*) OVER(PARTITION BY sor.order_id) > 1
        THEN TRUE
        ELSE FALSE
    END AS is_multiple_reviews,

    CASE
        WHEN sor.review_score IS NOT NULL
            AND sor.review_title IS NULL
            AND sor.review_message IS NULL
        THEN TRUE
        ELSE FALSE
    END AS is_rating_only,

    CASE
        WHEN sor.review_score IS NOT NULL
            AND sor.review_title IS NOT NULL
            AND sor.review_message IS NOT NULL
        THEN TRUE
        ELSE FALSE
    END AS is_full_review

FROM {{ ref("stg_order_reviews") }} sor

-- Joining customers dimension for taking customer_key
LEFT JOIN {{ ref("stg_orders") }} so
    ON sor.order_id = so.order_id
LEFT JOIN {{ ref("stg_customers") }} sc
    ON so.order_customer_id = sc.order_customer_id
LEFT JOIN {{ ref("dim_customers") }} dc
    ON sc.customer_id = dc.customer_id
    AND sor.review_created_timestamp >= dc.valid_from
    AND sor.review_created_timestamp < dc.valid_to