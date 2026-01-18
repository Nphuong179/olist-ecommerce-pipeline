{{ config(materialized='table') }}

WITH
    -- Calculate reference date (transactions occured in 2016-2028, we cannot use CURRENT_DATE)
    -- Using purchase timestamp instead of delivery timestamp for Customer Behaviour Analysis (= Purchase Decision)
    reference_date AS (
        SELECT
            MAX(order_purchase_timestamp)::DATE AS analysis_date
        FROM {{ ref('fact_orders') }}
    ),
    -- Aggregate customer metrics
    customer_orders AS (
        SELECT
            dc.customer_id,
            COUNT(fo.order_id) AS total_orders,
            MIN(fo.order_purchase_timestamp) AS first_order_date,
            MAX(fo.order_purchase_timestamp) AS latest_order_date,
            COUNT(CASE WHEN fo.order_status = 'canceled' THEN 1 END)::FLOAT 
                / NULLIF(COUNT(fo.order_id),0) AS order_cancellation_rate,
            SUM(CASE WHEN fo.delivered_on_time THEN 1 ELSE 0 END)::FLOAT 
                / NULLIF(COUNT(CASE WHEN fo.order_status = 'delivered' THEN 1 END),0) AS on_time_delivery_rate,
            SUM(fo.total_price) AS total_nmv,
            SUM(fo.total_freight_value) AS total_freight_paid,
            SUM(fo.total_price) / COUNT(fo.order_id) AS avg_nmv_per_order,

            CASE 
                WHEN COUNT(fo.order_id) > 1
                THEN DATE_DIFF('day', MIN(fo.order_purchase_timestamp), MAX(fo.order_purchase_timestamp))::FLOAT
                    / NULLIF(COUNT(fo.order_id) - 1,0)
                END AS avg_days_between_orders
        FROM {{ ref('dim_customers') }} dc
        JOIN {{ ref('fact_orders') }} fo
            ON dc.customer_key = fo.customer_key
        GROUP BY dc.customer_id
    ),

    -- Aggregate item-level metrics per customer
    customer_items AS (
        SELECT
            dc.customer_id,
            COUNT(DISTINCT foi.seller_key) AS unique_seller_purchased,
            COUNT(DISTINCT dp.category_name_portuguese) AS unique_categories_purchased,
            AVG(foi.freight_cost_share_of_price) AS avg_freight_share 
        FROM {{ ref('dim_customers') }} dc
        JOIN {{ ref('fact_order_items') }} foi
            ON dc.customer_key = foi.customer_key
        JOIN {{ ref("dim_products") }} dp
            ON foi.product_id = dp.product_id
        GROUP BY dc.customer_id
    ),

    -- Aggregate review behavior per customer
    customer_reviews AS (
        SELECT
            dc.customer_id,
            -- Review participation rate: % of orders with reviews
            COUNT(DISTINCT CASE WHEN fore.review_score IS NOT NULL THEN fo.order_id END)::FLOAT
                / NULLIF(COUNT(DISTINCT fo.order_id),0) AS review_participation_rate,
            -- Average review score: Satisfaction indicator (1-5 scale)
            -- NULL if customer never left a review
            AVG(fore.review_score) AS avg_review_score 
        FROM {{ ref("dim_customers") }} dc
        JOIN {{ ref("fact_orders") }} fo
            ON dc.customer_key = fo.customer_key
        JOIN {{ ref("fact_order_reviews") }} fore
            ON fo.order_id = fore.order_id
        GROUP BY dc.customer_id
    ),

    -- Aggregated payment behavior per customer
    customer_payment_counts AS (
        SELECT
            dc.customer_id,
            fop.payment_type,
            COUNT(DISTINCT fo.order_id) AS orders_using_payment
        FROM {{ ref('dim_customers') }} dc
        JOIN {{ ref("fact_orders") }} fo
            ON dc.customer_key = fo.customer_key
        JOIN {{ ref("fact_order_payments") }} fop
            ON fo.order_id = fop.order_id
        WHERE fop.is_primary_payment = TRUE -- only take method in primary payments
        GROUP BY dc.customer_id, fop.payment_type
    ),

    customer_total_orders AS (
        SELECT
            dc.customer_id,
            COUNT(DISTINCT fo.order_id) AS total_orders
        FROM {{ ref('dim_customers') }} dc
        JOIN {{ ref('fact_orders') }} fo
            ON dc.customer_key = fo.customer_key
        GROUP BY dc.customer_id
    ),

    customer_payment_ranked AS (
        SELECT
            cpc.customer_id,
            cpc.payment_type,
            cpc.orders_using_payment,
            cto.total_orders,
            cpc.orders_using_payment::FLOAT / NULLIF(cto.total_orders,0) AS payment_share,
            ROW_NUMBER() OVER(
                PARTITION BY cpc.customer_id 
                ORDER BY cpc.orders_using_payment DESC, cpc.payment_type ASC
            ) AS preference_rank
        FROM customer_payment_counts cpc
        JOIN customer_total_orders cto
            ON cpc.customer_id = cto.customer_id
    ),

    customer_payment_preference AS (
        SELECT
            customer_id,
            payment_type AS preferred_payment_method,
            payment_share AS preferred_payment_share,
            total_orders,
        -- Classify consistency
            CASE
                WHEN preferred_payment_share >= 0.9 THEN 'highly_consistent'
                WHEN preferred_payment_share >= 0.7 THEN 'somewhat_consistent'
                WHEN preferred_payment_share >= 0.5 THEN 'multi_method_user'
                ELSE 'payment_explorer'
            END AS payment_consistency_profile
        FROM customer_payment_ranked
        WHERE preference_rank = 1
    ),

    customer_payment_details AS (
        SELECT
            dc.customer_id,
            AVG(CASE WHEN fop.payment_type = 'credit_card' THEN fop.payment_installments END) AS avg_installments_when_using_credit,
            MAX(CASE WHEN fop.payment_type = 'credit_card' THEN fop.payment_installments END) AS max_installments_used,
            COUNT(DISTINCT CASE WHEN fop.is_only_payment = FALSE THEN fo.order_id END)::FLOAT 
                / NULLIF(COUNT(DISTINCT fo.order_id),0) AS mixed_payment_rate,
            SUM(CASE WHEN fop.payment_type = 'voucher' THEN fop.payment_value END)::FLOAT
                / NULLIF(SUM(fop.payment_value),0) AS voucher_using_rate
        FROM {{ ref('dim_customers') }} dc
        JOIN {{ ref("fact_orders") }} fo
            ON dc.customer_key = fo.customer_key
        JOIN {{ ref("fact_order_payments") }} fop
            ON fo.order_id = fop.order_id
        GROUP BY dc.customer_id
    )

SELECT
    -- Customer Identifier
    co.customer_id,

    -- Order Volume & Frequency
    co.total_orders,
    co.avg_days_between_orders, -- NULL indicates one-time buyers

    -- Order Timing
    co.first_order_date,
    co.latest_order_date, 
    DATE_DIFF('day', co.latest_order_date, rd.analysis_date) AS days_since_last_order,

    -- Order Quality
    co.order_cancellation_rate,
    co.on_time_delivery_rate, -- Rate among delivered orders only

    -- Financial Metrics
    co.total_nmv,
    co.total_freight_paid,
    co.avg_nmv_per_order,

    -- Review Behavior
    cr.review_participation_rate,
    cr.avg_review_score,
    
    -- Shopping Diversity
    ci.unique_seller_purchased,
    ci.unique_categories_purchased,
    ci.avg_freight_share, -- Freight cost as % of item price

    -- Payment Preference
    cpp.preferred_payment_method,
    cpp.preferred_payment_share, -- % of orders using preferred method
    cpp.payment_consistency_profile,

    -- Payment Details
    cpd.avg_installments_when_using_credit, -- NULL if never used credit card
    cpd.max_installments_used,
    cpd.voucher_using_rate,
    cpd.mixed_payment_rate
FROM customer_orders co
CROSS JOIN reference_date rd
JOIN customer_items ci
    ON co.customer_id = ci.customer_id
JOIN customer_reviews cr
    ON co.customer_id = cr.customer_id
JOIN customer_payment_preference cpp
    ON co.customer_id = cpp.customer_id
JOIN customer_payment_details cpd
    ON co.customer_id = cpd.customer_id