{{ config(materialized='table') }}
-- Purpose: Segment customers by current value and growth opportunity
-- Context: 97% of Olist customers are one-time buyer, retention is the primary challenge 
SELECT
    mcb.customer_id,

    CASE
        WHEN mcb.unique_categories_purchased <= 1 THEN 'niche_shopper'
        WHEN mcb.unique_categories_purchased = 2 THEN 'moderate_explorer'
        ELSE 'multi_category_buyer'
    END AS category_engagement,

    CASE
        WHEN mcb.avg_nmv_per_order < 100 THEN 'value_conscious'
        WHEN mcb.avg_nmv_per_order < 500 THEN 'mid_range'
        WHEN avg_nmv_per_order < 1000 THEN 'premium'
        ELSE 'luxury'
    END AS spending_tier,

    -- Composite growth strategy: Recommended action based on customer behavior profile
    CASE
        -- High spending + narrow categories -> Expand to adjacent categories
        WHEN total_nmv >= 2000 AND unique_categories_purchased <= 1
        THEN 'cross_category_expansion'
        -- Broad explorer + low NMV -> Increase items per order
        WHEN unique_categories_purchased >= 3 AND avg_nmv_per_order < 300
        THEN 'increase_basket_size'
        -- High NMV + infrequent -> Increase purchase frequency
        WHEN total_orders <= 3 AND avg_nmv_per_order >= 1000
        THEN 'increase_purchase_frequency'
        -- Satisfied one-time buyers with high NMV (best_recovery_potential)
        WHEN total_orders = 1 
            AND avg_nmv_per_order >= 500
            AND avg_review_score >= 4 -- They were satisfied
        THEN 'satisfied_buyer_recovery' 
        -- Dissatisfied high spenders (fix experience, then recover)
        WHEN total_orders = 1
            AND avg_nmv_per_order >= 500
            AND avg_review_score <= 2
        THEN 'dissatisfied_buyer_recovery'
        -- Medium value, medium frequency -> Standard engagement
        ELSE 'standard_engage' 
    END AS growth_strategy,
    
    CASE
        -- NEVER DELIVERED: Segment by recency and failure type
        -- Orders stuck, immediate investigation needed
        WHEN mcl.lifecycle_stage = 'never_delivered_stuck'
        THEN 'never_delivered_stuck'
    
        -- Stock-out failure < 60 days, re-engage with availability notification
        WHEN mcl.lifecycle_stage = 'never_delivered_stockout'
            AND mcb.days_since_last_order <= 30
        THEN 'never_delivered_recent_stockout'

        -- Canceled < 60 days ago, low recovery potential
        WHEN mcl.lifecycle_stage = 'never_delivered_canceled'
            AND mcb.days_since_last_order <= 60
        THEN 'never_delivered_recent_canceled'

        -- Failed attempt > 60 days ago, very low recovery probability
        WHEN mcl.lifecycle_stage LIKE 'never_delivered%'
            AND mcb.days_since_last_order > 60
        THEN 'never_delivered_code'

        -- AT-RISK: Prioritize by severity (experience > cost > behavior)
        -- Priority 1: Experience failures (most severe)
        -- Low satisfaction (< 3.5), needs service recovery before re-engagement
        WHEN mcl.lifecycle_stage LIKE '%at_risk'
            AND mcb.avg_review_score <= 3.5
        THEN 'at_risk_dissatisfied'

        -- Delivery issues, needs fulfillment improvement
        WHEN mcl.lifecycle_stage LIKE '%at_risk'
            AND mcb.on_time_delivery_rate <= 0.8
        THEN 'at_risk_poor_delivery'

        -- Frequent stock-outs, needs inventory management
        WHEN mcl.lifecycle_stage LIKE '%at_risk'
            AND mcb.unavailable_rate > 0
        THEN 'at_risk_frequent_stockouts'

        -- Priority 2: Cost burden (addressable)
        -- High shipping cost, offer free shipping promotions or nearby sellers
        WHEN mcl.lifecycle_stage LIKE '%at_risk'
            AND mcb.avg_freight_share >= 0.3
        THEN 'at_risk_freight_sensitive'

        -- Priority 3: Behavior pattern
        -- Only buys with promotions
        WHEN mcl.lifecycle_stage LIKE '%at_risk'
            AND mcb.voucher_using_rate >= 0.3
        THEN 'at_risk_promo_dependent'

        -- Priority 4: No clear issues 
        -- Good experience but stopped buying
        WHEN mcl.lifecycle_stage LIKE '%at_risk'
            AND mcb.avg_review_score > 3.5
            AND mcb.on_time_delivery_rate > 0.8
            AND mcb.unavailable_rate = 0
            AND mcb.avg_freight_share < 0.3
            AND mcb.voucher_using_rate < 0.3
        THEN 'at_risk_silent_churn'










    END AS recovery_segment,



    -- Growth potential score: Percentile-based scoring
    -- Component 1: Recency (35 pts)
    CASE
        WHEN days_since_last_order >= 30 THEN 35
        WHEN days_since_last_order >= 45 THEN 25
        WHEN days_since_last_order >= 60 THEN 15
        WHEN days_since_last_order >= 90 THEN 10
        ELSE 0
    END +
    -- Component 2: Order value potential (30 pts)
    CASE
        WHEN avg_nmv_per_order < 90 THEN 35
        WHEN avg_nmv_per_order < 150 THEN 20
        WHEN avg_nmv_per_order < 500 THEN 10
        ELSE 0
    END +
    -- Component 3: Delivered Orders (35 pts) - MOST IMPORTANT 
    CASE
        WHEN delivered_orders = 0 THEN 35
        WHEN delivered_orders = 1 THEN 25
        WHEN delivered_orders = 2 THEN 20
        WHEN delivered_orders > 2 THEN 10
    END
    AS recovery_priority_score,
    
    -- Supporting metrics
    total_nmv,
    delivered_orders,
    avg_nmv_per_order,
    unique_categories_purchased

FROM {{ ref("mart_customers_base") }} mcb
LEFT JOIN {{ ref("mart_customer_lifecycle") }} mcl
    ON mcb.customer_id = mcl.customer_id