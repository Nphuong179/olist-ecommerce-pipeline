{{ config(materialized='view') }}

SELECT
    TRIM(order_id) AS order_id,
    order_item_id AS item_sequence_number, -- Clear rename!
    TRIM(product_id) AS product_id,
    TRIM(seller_id) AS seller_id,

    CAST(shipping_limit_date AS TIMESTAMP) shipping_limit_timestamp,

    CAST(price AS NUMERIC) AS price,
    CAST(freight_value AS NUMERIC) AS freight_value
    
FROM {{ source("raw","order_items") }}