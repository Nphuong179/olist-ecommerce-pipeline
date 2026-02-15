{{ config(materialized='table') }}
-- Purpose: Segment customers by current value and growth opportunity
WITH customer_enriched AS (
    SELECT
        mcb.customer_id,
        mcl.lifecycle_stage,
        mcb.delivered_orders,
        mcb.avg_nmv_per_order,
        mcb.unique_categories_purchased,
        mcb.days_since_last_order,

        -- Core metrics
        mcb.avg_review_score,
        mcb.on_time_delivery_rate,
        mcb.unavailable_rate,
        mcb.avg_freight_share,
        mcb.voucher_using_rate,

        -- Issue flags
        (mcb.avg_review_score <= 3.5) AS has_satisfaction_issue,
        (mcb.on_time_delivery_rate <= 0.7) AS has_delivery_issue,
        (mcb.unavailable_rate > 0.3) AS has_stockout_issue,
        COALESCE((mcb.voucher_using_rate > 0.3), FALSE) AS has_promo_dependency,
        (mcb.avg_freight_share > 0.4) AS has_freight_burden

    FROM {{ ref("mart_customers_base") }} mcb
    LEFT JOIN {{ ref("mart_customer_lifecycle") }} mcl
        ON mcb.customer_id = mcl.customer_id
)

SELECT
    customer_id,
    lifecycle_stage,
    
    -- ISSUE FLAGS
    has_satisfaction_issue,
    has_delivery_issue,
    has_stockout_issue,
    has_promo_dependency,
    has_freight_burden,

    -- DERIVED AGGREGATIONS
    (
        CASE WHEN has_satisfaction_issue THEN 1 ELSE 0 END +
        CASE WHEN has_delivery_issue THEN 1 ELSE 0 END +
        CASE WHEN has_stockout_issue THEN 1 ELSE 0 END +
        CASE WHEN has_promo_dependency THEN 1 ELSE 0 END +
        CASE WHEN has_freight_burden THEN 1 ELSE 0 END
    ) AS total_issues,

    -- PRIMARY CLASSIFICATION
    CASE
        -- Priority 1: NEVER DELIVERED. Segment by recency and failure type
        -- Orders stuck, immediate investigation needed
        WHEN lifecycle_stage = 'never_delivered_stuck'
        THEN 'never_delivered_stuck'
    
        -- Stock-out failure < 60 days, re-engage with availability notification
        WHEN lifecycle_stage = 'never_delivered_stockout'
            AND days_since_last_order <= 30
        THEN 'never_delivered_recent_stockout'

        -- Canceled < 60 days ago, low recovery potential
        WHEN lifecycle_stage = 'never_delivered_canceled'
            AND days_since_last_order <= 60
        THEN 'never_delivered_recent_canceled'

        -- Failed attempt > 60 days ago, very low recovery probability
        WHEN lifecycle_stage LIKE 'never_delivered%'
            AND days_since_last_order > 60
        THEN 'never_delivered_cold'

        -- Priority 2: Growth opportunities (satisfied customers only)
        -- Middle value active customers
        WHEN avg_nmv_per_order BETWEEN 100 AND 500
            AND lifecycle_stage IN ('one_time_new', 'repeat_active')
        THEN 'increase_basket_size'

        -- High value active customers
        WHEN avg_nmv_per_order > 500
            AND lifecycle_stage IN ('one_time_new', 'repeat_active')
        THEN 'maintain_engagement'

        -- Niche shopper
        WHEN unique_categories_purchased = 1
            AND lifecycle_stage IN ('one_time_new', 'repeat_active')
        THEN 'category_expansion'

        -- Priority 3: Identifiable friction points
        -- Low satisfaction, needs service recovery before re-engagement
        WHEN total_issues > 0 THEN 'has_identifiable_issues'

        -- Priority 4: No clear action
        -- Hardest to recover. Good experience but still left without complaint. No clear intervention strategy
        WHEN lifecycle_stage LIKE '%at_risk'
        THEN 'silent_churn'
    END AS actionable_segment,

    CASE
        WHEN total_issues = 0 THEN 'no_issues'
        WHEN total_issues = 1 THEN 'single_issue'
        WHEN total_issues = 2 THEN 'dual_issues'
        ELSE 'multiple_issues'
    END AS issue_complexity,

    CASE
        WHEN actionable_segment LIKE 'never_delivered%' THEN 'acquisition_failed'
        WHEN actionable_segment IN ('dissatisfied', 'poor_delivery_experience', 'frequent_stockouts') THEN 'service_issues'
        WHEN actionable_segment IN ('promo_dependent', 'freight_sensitive') THEN 'price_sensitive'
        WHEN actionable_segment IN ('increase_basket_size', 'category_expansion', 'maintain_engagement') THEN 'growth_opportunity'
        WHEN actionable_segment IN ('silent_churn', 'mixed_factors') THEN 'churn_risk'
    END AS actionable_segment_group,

    -- Supporting metrics
    delivered_orders,
    avg_review_score,
    on_time_delivery_rate,
    unavailable_rate,
    avg_freight_share,
    voucher_using_rate,
    avg_nmv_per_order,
    unique_categories_purchased
FROM customer_enriched