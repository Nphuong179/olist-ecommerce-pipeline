{{ config(materialized='view') }}

SELECT
    TRIM(order_id) AS order_id,
    payment_sequential AS payment_transaction_number, -- Renaming for the clearer name
    TRIM(payment_type) AS payment_type,
    payment_installments AS payment_installments,
    CAST(payment_value AS NUMERIC) AS payment_value

FROM {{ source("raw", "order_payments") }}