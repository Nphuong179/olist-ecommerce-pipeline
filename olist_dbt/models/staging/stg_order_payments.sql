{{ config(materialized='view') }}

SELECT
    TRIM("order_id") AS order_id,
    "payment_sequential" AS payment_transaction_number, -- Renaming for the clearer name
    TRIM("payment_type") AS payment_type,
    "payment_installments" AS payment_installments,
    "payment_value"::DECIMAL(10,2) AS amount -- Clearer name

FROM {{ source("raw", "raw_order_payments")}}