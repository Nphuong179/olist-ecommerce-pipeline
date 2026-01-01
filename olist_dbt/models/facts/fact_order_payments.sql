{{ config(materialized='table') }}

WITH order_payment_aggregates AS (
    SELECT
        order_id,
        COUNT(*) AS payment_transaction_count,
        SUM(payment_value) AS total_payment,
        MAX(payment_value) AS largest_payment
    FROM {{ ref("stg_order_payments") }}
    GROUP BY order_id
)

SELECT
    -- Natural key
    sop.order_id,
    sop.payment_transaction_number,

    -- Payment attributes
    sop.payment_type,
    sop.payment_installments,

    -- Monetary values
    sop.payment_value,

    CASE
        WHEN opa.total_payment > 0
        THEN (sop.payment_value / opa.total_payment)
    END AS payment_share_of_order,

    CASE
        WHEN sop.payment_installments > 0
        THEN (sop.payment_value / sop.payment_installments)
    END AS monthly_installment_amount,

    -- Derived flag: Payment characteristics
    CASE
        WHEN sop.payment_value = opa.largest_payment
        THEN TRUE
        ELSE FALSE
    END AS is_primary_payment,

    CASE
        WHEN opa.payment_transaction_count = 1
        THEN TRUE
        ELSE FALSE
    END AS is_only_payment,

    CASE
        WHEN sop.payment_installments > 1
        THEN TRUE
        ELSE FALSE
    END AS is_installment_payment

FROM {{ ref("stg_order_payments") }} sop
LEFT JOIN order_payment_aggregates opa
    ON sop.order_id = opa.order_id