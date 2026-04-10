{{ config(materialized='view') }}

WITH global_avg AS (
    SELECT
        SUM(CASE WHEN delivered_on_time = FALSE THEN delivered_vs_estimated ELSE 0 END) /
        NULLIF(SUM(CASE WHEN delivered_on_time = FALSE THEN 1 ELSE 0 END), 0)  AS avg_hours_late
    FROM {{ ref("fact_orders") }}
    WHERE order_status = 'delivered'
)
SELECT
    -- Identifiers
    fo.order_id,

    -- Filter anchors
    fo.order_purchase_timestamp,
    dc.state,
    dc.region,

    -- Order status
    fo.order_status,

    -- Funnel stage flagg
    fo.order_approved_timestamp IS NOT NULL AS reached_approval,
    fo.order_delivered_carrier_timestamp IS NOT NULL AS reached_carrier,
    fo.order_delivered_customer_timestamp IS NOT NULL AS reached_delivery,

    -- Exit reasons
    CASE
        WHEN fo.order_status = 'canceled' THEN 'canceled'
        WHEN fo.order_status = 'unavailable' THEN 'unavailable'
        WHEN fo.order_status NOT IN ('delivered', 'canceled', 'unavailable') THEN 'stuck'
        ELSE NULL
    END AS exit_reason,

    -- Delivery performance
    fo.delivered_vs_estimated,
    fo.delivered_on_time,
    CAST(fo.order_estimated_delivery_date AS DATE) AS order_estimated_delivery_date,
    CAST(fo.order_delivered_customer_timestamp AS DATE) AS order_delivered_customer_timestamp,
    ga.avg_hours_late,
    fo.delivered_vs_estimated < ga.avg_hours_late * 1.5 AS is_severe_outlier,

    -- For scaling efficiency
    fo.quantity
FROM {{ ref("fact_orders") }} fo
LEFT JOIN {{ ref("dim_customers") }} dc
    ON fo.customer_key = dc.customer_key
CROSS JOIN global_avg ga