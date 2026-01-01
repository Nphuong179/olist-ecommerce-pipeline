{{ config(materialized='table') }}

SELECT
    -- Natural key
    soi.order_id,
    soi.item_sequence_number,

    -- Foreign key to dimension tables
    soi.product_id,
    ds.seller_key,
    dc.customer_key,

    -- Time-based filtering enabler at item level
    so.order_purchase_timestamp,

    -- Monetary values
    soi.price AS item_price,
    soi.freight_value,

    CASE
        WHEN soi.price > 0
        THEN (soi.freight_value / soi.price)
    END AS freight_cost_share_of_price,

    -- Shipping deadline
    soi.shipping_limit_timestamp,

    -- Derived metrics: Shipping performance
    CASE 
        WHEN soi.shipping_limit_timestamp IS NOT NULL
        THEN DATE_DIFF('hour', so.order_purchase_timestamp, soi.shipping_limit_timestamp) 
    END AS hours_to_shipping_limit,

    CASE
        WHEN so.order_delivered_carrier_timestamp IS NOT NULL
            AND soi.shipping_limit_timestamp IS NOT NULL
        THEN DATE_DIFF('hour', soi.shipping_limit_timestamp, so.order_delivered_carrier_timestamp)
    END AS hours_past_shipping_limit,

    CASE
        WHEN so.order_delivered_carrier_timestamp IS NOT NULL
            AND soi.shipping_limit_timestamp IS NOT NULL
        THEN CASE 
                WHEN so.order_delivered_carrier_timestamp <= soi.shipping_limit_timestamp
                THEN TRUE
                ELSE FALSE
            END
    END AS met_shipping_deadline,

    -- Derived flag: Freight value analysis
    CASE
        WHEN soi.price > 0
            AND (soi.freight_value / soi.price) > 0.5
        THEN TRUE
        ELSE FALSE
    END AS is_high_freight_item,

    CASE
        WHEN soi.freight_value = 0
        THEN TRUE
        ELSE FALSE
    END AS is_free_shipping

FROM {{ ref("stg_order_items") }} soi

-- Join stg_orders to take timestamp values
LEFT JOIN {{ ref("stg_orders") }} so
    ON soi.order_id = so.order_id

-- Join dimension tables to replace Natural key to Surrogate key
-- Joining dim_sellers
LEFT JOIN {{ ref("dim_sellers") }} ds
    ON soi.seller_id = ds.seller_id
    AND so.order_purchase_timestamp >= ds.valid_from
    AND so.order_purchase_timestamp < ds.valid_to
-- Joining dim_customers
LEFT JOIN {{ ref("stg_customers") }} sc
    ON so.order_customer_id = sc.order_customer_id
LEFT JOIN {{ ref("dim_customers") }} dc
    ON sc.customer_id = dc.customer_id
    AND so.order_purchase_timestamp >= dc.valid_from
    AND so.order_purchase_timestamp < dc.valid_to