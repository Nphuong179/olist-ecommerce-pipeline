{{ config(materialized='view') }}

SELECT
    TRIM("order_id") AS order_id,
    "order_item_id" AS item_sequence_number, -- Clear rename!
    TRIM("product_id") AS product_id,
    TRIM("seller_id") AS seller_id,

    "shipping_limit_date"::TIMESTAMP AS shipping_limit_timestamp,
    "shipping_limit_date"::DATE AS shipping_limit_date,

    "price"::DECIMAL(10,2) AS price,
    "freight_value"::DECIMAL(10,2) AS freight_value
    
FROM {{ source("raw","raw_order_items") }}