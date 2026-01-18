{{ config(materialized='table') }}
-- Purpose: Segment customers by current value and growth opportunity
-- Context: 97% of Olist customers are one-time buyer, retention is the primary challenge 
SELECT
    customer_id,

    CASE
        WHEN total_orders = 1 THEN 'one_time_buyer'
        WHEN total_orders = 2 THEN 'emerging_repeat'
        WHEN total_orders <= 5 THEN 'active_buyer'
        ELSE 'loyal_customer'
    END AS engagement_level,

    CASE
        WHEN unique_categories_purchased <= 1 THEN 'niche_shopper'
        WHEN unique_categories_purchased = 2 THEN 'moderate_explorer'
        ELSE 'multi_category_buyer'
    END AS category_engagement,

    CASE
        WHEN avg_nmv_per_order < 100 THEN 'value_conscious'
        WHEN avg_nmv_per_order < 500 THEN 'mid_range'
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

    -- Growth potential score: Percentile-based scoring
    -- Component 1: Category potential (30 pts)
    CASE
        WHEN unique_categories_purchased = 1 THEN 30 -- 96th percentile
        WHEN unique_categories_purchased = 2 THEN 10 -- 98th percentile
        ELSE 0
    END +
    -- Component 2: Order value potential (35 pts)
    CASE
        WHEN avg_nmv_per_order < 90 THEN 35 -- Bottom 50% (high potential)
        WHEN avg_nmv_per_order < 150 THEN 20 -- 50-70th percentile
        WHEN avg_nmv_per_order < 500 THEN 10 -- 70-90th percentile
        ELSE 0 -- Top 10% (low potential)
    END +
    -- Component 3: Frequency potential (35 pts) - MOST IMPORTANT
    CASE
        WHEN total_orders = 1 THEN 35 -- 97th percentile
        WHEN total_orders = 2 THEN 20 -- 99th percentile
        WHEN total_orders = 3 THEN 10 -- 99.5th percentile
        ELSE 0  -- Top 5%
    END
    AS growth_potential_score,
    
    -- Supporting metrics
    total_nmv,
    total_orders,
    avg_nmv_per_order,
    unique_categories_purchased

FROM {{ ref("mart_customers_base") }}