{{ config(materialized='view') }}

WITH 
    base AS (
        SELECT
            region,
            COUNT(order_id) AS purchased,
            SUM(CASE WHEN reached_approval = TRUE THEN 1 ELSE 0 END) AS approved,
            SUM(CASE WHEN reached_carrier = TRUE THEN 1 ELSE 0 END) AS shipped,
            SUM(CASE WHEN reached_delivery = TRUE THEN 1 ELSE 0 END) AS delivered
        FROM {{ ref("mart_order_fulfillment") }}
        GROUP BY region
    ),
    orders_in_stages AS (
        SELECT
            'Purchase' AS stage_name,
            1 AS stage_order,
            region,
            purchased as order_count
        FROM base
        UNION ALL
        SELECT
            'Approved' AS stage_name,
            2 AS stage_order,
            region,
            approved AS order_count
        FROM base
        UNION ALL
        SELECT
            'Shipped' AS stage_name,
            3 AS stage_order,
            region,
            shipped AS order_count
        FROM base
        UNION ALL
        SELECT
            'Delivered' AS stage_name,
            4 AS stage_order,
            region,
            delivered AS order_count
        FROM base
    )
SELECT
    stage_name,
    stage_order,
    region,
    order_count,
    order_count / MAX(order_count) OVER(PARTITION BY region) AS pct_of_purchased
FROM orders_in_stages
