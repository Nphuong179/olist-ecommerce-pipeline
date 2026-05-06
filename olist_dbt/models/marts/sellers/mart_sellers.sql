{{ config(materialized='table') }}

WITH 
    reference_date AS (
        SELECT DATE '2018-08-31' AS analysis_date
    ),

    seller_metrics AS (
        SELECT
            ds.seller_id,
            ds.region,
            ds.state,
            ds.city,
            COUNT(DISTINCT fo.order_id) AS total_orders,
            MAX(fo.order_purchase_timestamp) AS latest_sale_date,
            MIN(fo.order_purchase_timestamp) AS first_sale_date,
            CAST(SUM(CASE WHEN foi.met_shipping_deadline THEN 1 ELSE 0 END) AS FLOAT64)
                / NULLIF(COUNT(*), 0) AS met_shipping_deadline_rate
        FROM {{ ref("dim_sellers") }} ds
        JOIN {{ ref("fact_order_items") }} foi
            ON ds.seller_key = foi.seller_key
        JOIN {{ ref("fact_orders") }} fo
            ON foi.order_id = fo.order_id
        WHERE fo.order_purchase_timestamp < '2018-09-01'
            AND fo.order_status = 'delivered'
        GROUP BY
            ds.seller_id,
            ds.region,
            ds.state,
            ds.city
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
            sm.seller_id,
            TIMESTAMP_DIFF(CAST(rd.analysis_date AS TIMESTAMP), sm.latest_sale_date, DAY) AS days_since_last_sale
        FROM seller_metrics sm
        CROSS JOIN reference_date rd
    ),

    seller_combined AS (
        SELECT
            sm.seller_id,
            sm.city,
            sm.state,
            sm.region,
            sm.total_orders,
            sm.latest_sale_date,
            sm.first_sale_date,
            TIMESTAMP_DIFF(sm.latest_sale_date, sm.first_sale_date, DAY) / NULLIF(sm.total_orders - 1, 0) AS avg_days_between_orders,
            CASE WHEN sm.total_orders = 1 THEN TRUE ELSE FALSE END AS is_single_order_seller,
            sm.met_shipping_deadline_rate, 
            srm.avg_review_score,
            sr.days_since_last_sale
        FROM seller_metrics sm
        LEFT JOIN seller_review_metrics srm
            ON sm.seller_id = srm.seller_id
        JOIN seller_recency sr
            ON sm.seller_id = sr.seller_id
    ),

    percentiles_threshold AS (
        SELECT 
            total_orders_p75,
            total_orders_p25,
            avg_days_between_orders_p25,
            days_since_last_sale_p75,
            days_since_last_sale_p25
        FROM (
            SELECT 
                APPROX_QUANTILES(total_orders, 100)[OFFSET(75)] AS total_orders_p75,
                APPROX_QUANTILES(total_orders, 100)[OFFSET(25)] AS total_orders_p25,
                APPROX_QUANTILES(avg_days_between_orders, 100)[OFFSET(25)] AS avg_days_between_orders_p25
            FROM seller_combined
            WHERE is_single_order_seller = FALSE
        )
        CROSS JOIN (
            SELECT
                APPROX_QUANTILES(days_since_last_sale, 100)[OFFSET(75)] AS days_since_last_sale_p75,
                APPROX_QUANTILES(days_since_last_sale, 100)[OFFSET(25)] AS days_since_last_sale_p25
            FROM seller_combined
        )
    )

SELECT 
    -- Unique itendifier
    sc.seller_id,

    -- Seller segmentation
    -- Active
    CASE
        WHEN sc.total_orders > pt.total_orders_p75
            AND sc.days_since_last_sale <= pt.days_since_last_sale_p25
        THEN 'established_active'

        WHEN sc.total_orders <= pt.total_orders_p75
            AND sc.total_orders > pt.total_orders_p25
            AND sc.days_since_last_sale <= pt.days_since_last_sale_p25
        THEN 'standard_active'

        WHEN sc.total_orders <= pt.total_orders_p25
            AND sc.days_since_last_sale <= pt.days_since_last_sale_p25
        THEN 'small_active'

    -- At-risk
        WHEN sc.total_orders > pt.total_orders_p75
            AND sc.days_since_last_sale > pt.days_since_last_sale_p25
            AND sc.days_since_last_sale <= pt.days_since_last_sale_p75
        THEN 'established_at_risk'

        WHEN sc.total_orders <= pt.total_orders_p75
            AND sc.total_orders > pt.total_orders_p25
            AND sc.days_since_last_sale > pt.days_since_last_sale_p25
            AND sc.days_since_last_sale <= pt.days_since_last_sale_p75
        THEN 'standard_at_risk'

        WHEN sc.total_orders <= pt.total_orders_p25
            AND sc.days_since_last_sale > pt.days_since_last_sale_p25
            AND sc.days_since_last_sale <= pt.days_since_last_sale_p75
        THEN 'small_at_risk'

    -- Inactive
        WHEN sc.total_orders > pt.total_orders_p75
            AND sc.days_since_last_sale > pt.days_since_last_sale_p75
        THEN 'established_inactive'

        WHEN sc.total_orders <= pt.total_orders_p75
            AND sc.total_orders > pt.total_orders_p25
            AND sc.days_since_last_sale > pt.days_since_last_sale_p75
        THEN 'standard_inactive'

        WHEN sc.total_orders <= pt.total_orders_p25
            AND sc.days_since_last_sale > pt.days_since_last_sale_p75
        THEN 'small_inactive'

    END AS seller_segments,

    -- Supporting metrics
    sc.city,
    sc.state,
    sc.region,
    sc.total_orders,
    ROUND(sc.met_shipping_deadline_rate, 2) AS met_shipping_deadline_rate,
    ROUND(sc.avg_review_score, 2) AS avg_review_score,
    sc.first_sale_date,
    sc.latest_sale_date,
    sc.days_since_last_sale,
    ROUND(sc.avg_days_between_orders, 0) AS avg_days_between_orders
FROM seller_combined sc
CROSS JOIN percentiles_threshold pt