{{ config(materialized='view') }}

SELECT
    TRIM(order_id) AS order_id,
    TRIM(customer_id) AS order_customer_id, -- Links to customers
    TRIM(order_status) AS order_status,

    CAST(order_purchase_timestamp AS TIMESTAMP) AS order_purchase_timestamp,
    CAST(order_approved_at AS TIMESTAMP) AS order_approved_timestamp,
    CAST(order_delivered_carrier_date AS TIMESTAMP) AS order_delivered_carrier_timestamp,
    CAST(order_delivered_customer_date AS TIMESTAMP) AS order_delivered_customer_timestamp,
    CAST(order_estimated_delivery_date AS DATE) AS order_estimated_delivery_date

FROM {{ source("raw", "orders") }}