{{ config(materialized='view') }}

SELECT
    TRIM(customer_id) AS order_customer_id, -- Links to orders (one per order)
    TRIM(customer_unique_id) AS customer_id, -- Actual customer indentifier

    -- Address reference: Remove redundant prefix
    CAST(customer_zip_code_prefix AS STRING) AS zip_code_prefix,
    TRIM(customer_city) AS city,
    TRIM(customer_state) AS state

FROM {{ source("raw", "customers") }}