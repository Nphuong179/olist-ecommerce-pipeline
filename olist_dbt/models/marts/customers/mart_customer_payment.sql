{{ config(materialized='table') }}

-- Purpose: Segment customers by payment behavior and cost sensitivities
SELECT
    customer_id,

    -- Installment behavior: classify credit card usage patterns
    CASE
        WHEN avg_installments_when_using_credit IS NULL THEN 'never_used_credit'
        WHEN avg_installments_when_using_credit >= 10 THEN 'installment_preferred'
        WHEN avg_installments_when_using_credit >= 5 THEN 'installment_moderate'
        WHEN avg_installments_when_using_credit >1 THEN 'installment_occasional'
        ELSE 'full_payment_preferred'
    END AS installment_behavior,

    -- Promotion sensitivity: Identify discount-driven behavior
    CASE
        WHEN voucher_using_rate >= 0.3 THEN 'promotion_driven'
        WHEN voucher_using_rate >= 0.15 THEN 'promotion_aware'
        WHEN voucher_using_rate >= 0.1 THEN 'occasional_voucher_user'
        ELSE 'full_price_buyer'
    END AS promotion_sensitivity,

    -- Payment consistency
    payment_consistency_profile,

    -- Optimization segment: Customer segment for targeted marketing actions
    -- Hierarchy: (1): Credit acquisition, (2): Freight reduction, (3): Installment preference, (4): Promotion targeting
    CASE
        -- Credit card acquisition (long-term value)
        -- Offer substantial promotion for first credit card purchase
        WHEN total_orders >= 3
            AND avg_installments_when_using_credit IS NULL
        THEN 'credit_acquisition_prospect'
        -- Freight reduction (reduces cart abandon)
        -- Suggest nearby sellers or free shipping products
        WHEN avg_freight_share >= 0.2
        THEN 'freight_sensitive_shopper'
        -- Installment optimization
        -- Suggest products with 12+ installment options
        WHEN avg_installments_when_using_credit >= 10
        THEN 'installment_preferred_buyer'
        -- Promotion targeting (maintain engagement)
        -- Suggest product with active discount promotion
        WHEN voucher_using_rate >= 0.3
        THEN 'promotion_driven_shopper'
        
        ELSE 'standard_buyer' 
    END AS optimization_segment,

    -- Supporting metrics
    preferred_payment_method,
    preferred_payment_share,
    avg_installments_when_using_credit,
    max_installments_used,
    voucher_using_rate,
    mixed_payment_rate,
    avg_freight_share,
    total_orders

FROM {{ ref('mart_customers_base') }}