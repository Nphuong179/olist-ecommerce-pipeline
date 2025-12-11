{{ config(materialized='view') }}

SELECT
    TRIM("order_id") AS order_id,
    TRIM("customer_id") AS order_customer_id, -- Links to customers
    TRIM("order_status") AS order_status,

    "order_purchase_timestamp"::TIMESTAMP AS order_purchase_timestamp,
    "order_purchase_timestamp"::DATE AS order_purchase_date,
    "order_approved_at"::TIMESTAMP AS order_approved_timestamp,
    "order_delivered_carrier_date"::TIMESTAMP AS order_delivered_carrier_timestamp,
    "order_delivered_customer_date"::TIMESTAMP AS order_delivered_customer_date,
    "order_estimated_delivery_date"::DATE AS order_estimated_delivery_date

FROM {{ source("raw", "raw_orders") }}