{{ config(materialized='table') }}
-- Purpose: Identify customer lifecycle stage and reactivation opportunities

WITH median_repurchase AS (
        SELECT 
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY avg_days_between_orders) AS median_repurchase_interval
        FROM (
            SELECT
                dc.customer_id,
                DATE_DIFF('day', MIN(fo.order_purchase_timestamp), MAX(fo.order_purchase_timestamp))::FLOAT
                    / NULLIF(COUNT(fo.order_id) - 1, 0) AS avg_days_between_orders
            FROM {{ ref("dim_customers") }} dc
            JOIN {{ ref("fact_orders") }} fo
                ON dc.customer_key = fo.customer_key
            GROUP BY dc.customer_id
            HAVING COUNT(fo.order_id) > 1 -- Only repeat customers
        )
    )

SELECT
    customer_id,
    
    -- Lifecycle classification
    CASE
        -- NEVER DELIVERED: Failed acquisition - no successful orders
        -- Never reached terminal status
        WHEN delivered_orders = 0
            AND latest_order_status IN ('approved', 'shipped', 'processing', 'invoiced', 'created')
        THEN 'never_delivered_stuck'

        -- Customer canceled the order attempt
        WHEN delivered_orders = 0
            AND latest_order_status = 'canceled'
        THEN 'never_delivered_canceled'

        -- Platform could not fulfill due to inventory stockout
        WHEN delivered_orders = 0
            AND latest_order_status = 'unavailable'
        THEN 'never_delivered_stockout'

        -- ONE-TIME DELIVERY: Received exactly one order
        -- Recent first-time buyer, still within expected return window
        WHEN delivered_orders = 1 
            AND days_since_last_order <= 60 
        THEN 'one_time_new'

        -- First-time buyer who has not returned beyond expected window
        WHEN delivered_orders = 1 
            AND days_since_last_order > 60 
        THEN 'one_time_at_risk'

        -- REPEAT CUSTOMERS: Received 2+ orders
        -- Repeat buyer purchasing on expected window
        WHEN avg_days_between_orders IS NOT NULL 
            AND days_since_last_order <= avg_days_between_orders * 1.2
        THEN 'repeat_active'

        -- Repeat buyer overdue for next purchase, still recoverable
        WHEN avg_days_between_orders IS NOT NULL
            AND days_since_last_order <= avg_days_between_orders * 2.0 
        THEN 'repeat_at_risk'

        -- Repeat buyer significantly overdue, low recovery probability
        ELSE 'repeat_lapsed'
    END AS lifecycle_stage,
    
    -- Days overdue (negative = early, positive = late)
    -- For one-time buyer without avg_days_between_orders, use median_repurchase_interval instead
    days_since_last_order - COALESCE(avg_days_between_orders, median_repurchase_interval) as days_overdue,

    -- Recovery priority score
    CASE
        WHEN days_since_last_order > 0
        THEN total_nmv / days_since_last_order -- Higher spending + more recent = higher priority
        ELSE total_nmv
    END AS recovery_priority_score,

    -- Supporting metrics
    delivered_orders,
    total_nmv,
    avg_days_between_orders,
    days_since_last_order

FROM {{ ref("mart_customers_base") }}
CROSS JOIN median_repurchase
    
