{{ config(materialized='table') }}

WITH 
    reference_date AS (
        SELECT DATE '2018-08-31' AS analysis_date
    ),

    seller_order_metrics AS (
        SELECT
            ds.seller_id,
            COUNT(DISTINCT fo.order_id) AS total_orders,
            MAX(fo.order_purchase_timestamp) AS latest_sale_date
        FROM {{ ref("dim_sellers") }} ds
        JOIN {{ ref("fact_order_items") }} foi
            ON ds.seller_key = foi.seller_key
        JOIN {{ ref("fact_orders") }} fo
            ON foi.order_id = fo.order_id
        WHERE fo.order_purchase_timestamp < '2018-09-01'
        GROUP BY ds.seller_id
    ),

    seller_item_metrics AS (
        SELECT
            ds.seller_id,
            CAST(SUM(CASE WHEN foi.met_shipping_deadline THEN 1 ELSE 0 END) AS FLOAT64)
                / NULLIF(COUNT(*), 0) AS met_shipping_deadline_rate
        FROM {{ ref("dim_sellers") }} ds
        JOIN {{ ref("fact_order_items") }} foi
            ON ds.seller_key = foi.seller_key
        JOIN {{ ref("fact_orders") }} fo
            ON foi.order_id = fo.order_id
        WHERE fo.order_purchase_timestamp < '2018-09-01'
        GROUP BY ds.seller_id
    ),

    seller_review_metrics AS (
        SELECT
            ds.seller_id,
            AVG(fore.review_score) AS avg_review_score
        FROM {{ ref("dim_sellers") }} ds
        JOIN {{ ref("fact_order_items") }} foi
            ON ds.seller_key = foi.seller_key
        JOIN {{ ref("fact_order_reviews") }} fore
            ON foi.order_id = fore.order_id
        GROUP BY ds.seller_id
    ),

    seller_recency AS (
        SELECT
            som.seller_id,
            TIMESTAMP_DIFF(CAST(rd.analysis_date AS TIMESTAMP), som.latest_sale_date, DAY) AS days_since_last_sale
        FROM seller_order_metrics som
        CROSS JOIN reference_date rd
    ),

    seller_combined AS (
        SELECT
            som.seller_id,
            som.total_orders,
            som.latest_sale_date,
            sim.met_shipping_deadline_rate, 
            srm.avg_review_score,
            sr.days_since_last_sale
        FROM seller_order_metrics som
        LEFT JOIN seller_item_metrics sim
            ON som.seller_id = sim.seller_id
        LEFT JOIN seller_review_metrics srm
            ON som.seller_id = srm.seller_id
        JOIN seller_recency sr
            ON som.seller_id = sr.seller_id
    )

SELECT 
    -- Unique itendifier
    seller_id,

    CASE
        -- High engagement + High quality + Low volume
        WHEN total_orders <= 200
            AND days_since_last_sale <= 10
            AND avg_review_score >= 4
            AND met_shipping_deadline_rate >= 0.9
        THEN 'rising_star'

        -- High engagement + High quality + High volume
        WHEN total_orders >= 500
            AND days_since_last_sale <= 10
            AND avg_review_score >= 4
            AND met_shipping_deadline_rate >= 0.9
        THEN 'elite_seller'

        -- Active + High quality + Low volume
        WHEN total_orders <= 100
            AND days_since_last_sale <= 30
            AND avg_review_score >= 4
            AND met_shipping_deadline_rate >= 0.9
        THEN 'underexposed_gem'

        -- Active + Declining quality
        WHEN total_orders >= 300
            AND days_since_last_sale <= 30
            AND (avg_review_score <= 3 OR met_shipping_deadline_rate <= 0.8)
        THEN 'quality_at_risk'

        -- Inactive regardless of quality
        WHEN days_since_last_sale > 180
        THEN 'inactive_churned'

        -- Poor quality regardless of activity
        WHEN avg_review_score < 3
            OR met_shipping_deadline_rate < 0.5
        THEN 'underperforming'

        ELSE 'standard_seller'
    END AS seller_growth_segment,

    -- Underexposure potential score
    
    (
        -- Quality component: Review score
        CASE
            WHEN avg_review_score >= 4.5 THEN 50
            WHEN avg_review_score >= 4.0 THEN 35
            WHEN avg_review_score >= 3.5 THEN 20
            ELSE 0 
        END +

        -- Quality component: Fulfillment reliability
        CASE
            WHEN met_shipping_deadline_rate >= 0.95 THEN 50
            WHEN met_shipping_deadline_rate >= 0.90 THEN 40
            WHEN met_shipping_deadline_rate >= 0.80 THEN 35
            WHEN met_shipping_deadline_rate >= 0.70 THEN 10
            ELSE 0
        END
    ) *

    -- Underexposure component: Low volume order
    CASE
        WHEN total_orders <= 100 THEN 1.0
        WHEN total_orders <= 200 THEN 0.9
        WHEN total_orders <= 300 THEN 0.8
        WHEN total_orders <= 400 THEN 0.7
        WHEN total_orders <= 500 THEN 0.6
        ELSE 0
    END *

    -- Engagement component: Recency
    CASE
        WHEN days_since_last_sale <= 10 THEN 1
        WHEN days_since_last_sale <= 15 THEN 0.9
        WHEN days_since_last_sale <= 20 THEN 0.8
        WHEN days_since_last_sale <= 30 THEN 0.7
        ELSE 0 
    END AS underexposure_potential_score,

    -- Supporting metrics
    total_orders,
    met_shipping_deadline_rate,
    avg_review_score,
    latest_sale_date,
    days_since_last_sale
FROM seller_combined