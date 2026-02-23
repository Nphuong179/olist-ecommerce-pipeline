{{ config(materialized='table') }}

WITH
    -- Calculate reference date (transactions occured in 2016-2028, we cannot use CURRENT_DATE)
    -- Using purchase timestamp instead of delivery timestamp for Customer Behaviour Analysis (= Purchase Decision)
    reference_date AS (
        SELECT DATE '2018-08-31' AS analysis_date
    ),

    -- Value calculations from successfully delivered orders
    customer_financial_metrics AS (
        SELECT
            dc.customer_id,
            COUNT(fo.order_id) AS delivered_orders,
            SUM(CASE WHEN fo.delivered_on_time THEN 1 ELSE 0 END)::FLOAT 
                / NULLIF(SUM(CASE WHEN fo.delivered_on_time IS NOT NULL THEN 1 ELSE 0 END), 0) AS on_time_delivery_rate,
            SUM(fo.total_price) AS total_nmv,
            SUM(fo.total_price) / COUNT(fo.order_id) AS avg_nmv_per_order
        FROM {{ ref('dim_customers') }} dc
        JOIN {{ ref('fact_orders') }} fo
            ON dc.customer_key = fo.customer_key
        WHERE fo.order_purchase_timestamp < '2018-09-01'
            AND fo.order_status = 'delivered'
        GROUP BY dc.customer_id
    ),

    order_sequence AS (
        SELECT
            dc.customer_id,
            fo.order_id,
            fo.order_status,
            fo.order_purchase_timestamp,
            ROW_NUMBER() OVER(PARTITION BY dc.customer_id ORDER BY fo.order_purchase_timestamp DESC) AS order_recency,
            ROW_NUMBER() OVER(PARTITION BY dc.customer_id ORDER BY fo.order_purchase_timestamp ASC) AS order_sequence
        FROM {{ ref("dim_customers") }} dc
        LEFT JOIN {{ ref("fact_orders") }} fo
            ON dc.customer_key = fo.customer_key
    ),

    customer_latest_status AS (
        SELECT
            customer_id,
            order_status AS latest_order_status
        FROM order_sequence
        WHERE order_recency = 1
    ),

    customer_first_order AS (
        SELECT
            customer_id,
            order_id AS first_order_id
        FROM order_sequence
        WHERE order_sequence = 1
    ),

    -- Customer engagement across all order attempts
    customer_behavior_metrics AS (
        SELECT
            dc.customer_id,
            COUNT(fo.order_id) AS total_orders,
            MIN(fo.order_purchase_timestamp) AS first_order_date,
            MAX(fo.order_purchase_timestamp) AS latest_order_date,
            CASE
                WHEN COUNT(fo.order_id) > 1
                THEN DATE_DIFF('day', MIN(fo.order_purchase_timestamp), MAX(fo.order_purchase_timestamp))::FLOAT
                    / NULLIF(COUNT(fo.order_id) - 1, 0)
                END AS avg_days_between_orders,
            COUNT(CASE WHEN fo.order_status = 'canceled' THEN 1 END)::FLOAT
                / NULLIF(COUNT(fo.order_id), 0) AS order_cancellation_rate,
            COUNT(CASE WHEN fo.order_status = 'unavailable' THEN 1 END)::FLOAT
                / NULLIF(COUNT(fo.order_id),0) AS unavailable_rate
        FROM {{ ref("dim_customers") }} dc
        JOIN {{ ref("fact_orders") }} fo
            ON dc.customer_key = fo.customer_key
        WHERE fo.order_purchase_timestamp < '2018-09-01'
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
        WHERE foi.order_purchase_timestamp < '2018-09-01'
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
    cbm.customer_id,

    -- Order Volume & Frequency
    cls.latest_order_status,
    cbm.total_orders,
    COALESCE(cfm.delivered_orders,0) AS delivered_orders, 
    cbm.avg_days_between_orders, -- NULL indicates one-time buyers
    cfo.first_order_id,

    -- Order Timing
    cbm.first_order_date,
    cbm.latest_order_date, 
    DATE_DIFF('day', cbm.latest_order_date, rd.analysis_date) AS days_since_last_order,

    -- Order Quality
    cbm.order_cancellation_rate,
    cbm.unavailable_rate,
    cfm.on_time_delivery_rate, -- Rate among delivered orders only

    -- Financial Metrics
    cfm.total_nmv,
    cfm.avg_nmv_per_order,

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
    COALESCE(cpd.voucher_using_rate,0) AS voucher_using_rate,
    cpd.mixed_payment_rate
FROM customer_behavior_metrics cbm
CROSS JOIN reference_date rd
LEFT JOIN customer_latest_status cls
    ON cbm.customer_id = cls.customer_id
LEFT JOIN customer_first_order cfo
    ON cbm.customer_id = cfo.customer_id 
LEFT JOIN customer_financial_metrics cfm
    ON cbm.customer_id = cfm.customer_id
LEFT JOIN customer_items ci
    ON cbm.customer_id = ci.customer_id
LEFT JOIN customer_reviews cr
    ON cbm.customer_id = cr.customer_id
LEFT JOIN customer_payment_preference cpp
    ON cbm.customer_id = cpp.customer_id
LEFT JOIN customer_payment_details cpd
    ON cbm.customer_id = cpd.customer_id