{{ config(materialized='table') }}
-- Purpose: Segment customers by current value and growth opportunity
WITH 
    customer_enriched AS (
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
    ),
    primary_classification AS (
        SELECT
            customer_id,
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

                -- Priority 3: No clear action
                -- Hardest to recover. Good experience but still left without complaint. No clear intervention strategy
                WHEN lifecycle_stage LIKE '%at_risk'
                THEN 'silent_churn'
            END AS actionable_segment
        FROM customer_enriched
    )

SELECT
    ce.customer_id,
    ce.lifecycle_stage,
    
    -- ISSUE FLAGS
    ce.has_satisfaction_issue,
    ce.has_delivery_issue,
    ce.has_stockout_issue,
    ce.has_promo_dependency,
    ce.has_freight_burden,

    -- DERIVED AGGREGATIONS
    (
        CASE WHEN ce.has_satisfaction_issue THEN 1 ELSE 0 END +
        CASE WHEN ce.has_delivery_issue THEN 1 ELSE 0 END +
        CASE WHEN ce.has_stockout_issue THEN 1 ELSE 0 END +
        CASE WHEN ce.has_promo_dependency THEN 1 ELSE 0 END +
        CASE WHEN ce.has_freight_burden THEN 1 ELSE 0 END
    ) AS total_issues,

    pc.actionable_segment,

    CASE
        WHEN pc.actionable_segment LIKE 'never_delivered%' THEN 'acquisition_failed'
        WHEN pc.actionable_segment IN ('dissatisfied', 'poor_delivery_experience', 'frequent_stockouts') THEN 'service_issues'
        WHEN pc.actionable_segment IN ('promo_dependent', 'freight_sensitive') THEN 'price_sensitive'
        WHEN pc.actionable_segment IN ('increase_basket_size', 'category_expansion', 'maintain_engagement') THEN 'growth_opportunity'
        WHEN pc.actionable_segment IN ('silent_churn', 'mixed_factors') THEN 'churn_risk'
    END AS actionable_segment_group,

    -- Supporting metrics
    ce.delivered_orders,
    ce.avg_review_score,
    ce.on_time_delivery_rate,
    ce.unavailable_rate,
    ce.avg_freight_share,
    ce.voucher_using_rate,
    ce.avg_nmv_per_order,
    ce.unique_categories_purchased
FROM customer_enriched ce
JOIN primary_classification pc
    ON ce.customer_id = pc.customer_id