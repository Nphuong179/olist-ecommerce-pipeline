{{ config(materialized='table') }}

WITH
    -- Aggregate order_items to order level
    order_items_aggregates AS (
        SELECT 
            soi.order_id,
            MAX(soi.item_sequence_number) AS quantity,
            COUNT(DISTINCT soi.product_id) AS unique_product_count,
            COUNT(DISTINCT sp.category_name_portuguese) AS unique_category_count,
            COUNT(DISTINCT soi.seller_id) AS unique_seller_count,
            SUM(soi.price) AS total_price,
            SUM(soi.freight_value) AS total_freight_value,
            SUM(soi.price + soi.freight_value) AS total_order_amount
        FROM {{ ref("stg_order_items") }} soi
        LEFT JOIN {{ ref("stg_products") }} sp
            ON soi.product_id = sp.product_id
        GROUP BY soi.order_id
    ),
    -- Aggregate order_payments to order level
    order_payments_aggregates AS (
        SELECT
            order_id,
            COUNT(*) AS payment_transaction_count,
            COUNT(DISTINCT payment_type) AS unique_payment_types,
            MAX(payment_installments) AS installments_count,
            SUM(amount) AS total_payment_amount
        FROM {{ ref("stg_order_payments") }}
        GROUP BY order_id
    ),

SELECT
    so.order_id,
    so.order_status,
    
    --Foreign key to customers table (using surrogate key)
    c.customer_key,

    -- Degenerate dimensions
    so.order_id,
    so.order_status,

    -- Datetime attributes
    so.order_purchase_timestamp,
    so.order_approved_timestamp,
    so.order_delivered_carrier_timestamp,
    so.order_delivered_customer_timestamp,
    so.order_estimated_delivery_date,

    -- Measure preserve NULL for imcomplete/canceled orders
    -- NULL indicates the order didn't reach the stage when the metrics updated
    -- Measures: Order size and diversity
    oi.quantity,
    oi.unique_product_count,
    oi.unique_category_count,
    oi.unique_seller_count,

    -- Measure: Monetary values
    oi.total_price,
    oi.total_freight_value,
    oi.total_order_amount,
    op.total_payment_amount,

    -- Measures: Payment characteristics
    op.payment_transaction_count,
    op.unique_payment_types,
    op.installments_count,

    -- Payment vs. order value comparison
    op.total_payment_amount - oi.total_order_amount,

    -- Derived metrics: Time durations (in hours)
    CASE
        WHEN so.order_approved_timestamp IS NOT NULL
        THEN DATE_DIFF('hour', so.order_purchase_timestamp, so.order_approved_timestamp)
    END AS hours_to_approval,

    CASE
        WHEN so.order_delivered_carrier_timestamp IS NOT NULL
        THEN DATE_DIFF('hour', so.order_purchase_timestamp, so.order_delivered_carrier_timestamp)
    END AS hours_to_carrier,

    CASE
        WHEN so.order_delivered_customer_timestamp IS NOT NULL
        THEN DATE_DIFF('hour', so.order_purchase_timestamp, so.order_delivered_customer_timestamp)
    END AS hours_to_delivered,

    CASE
        WHEN so.order_delivered_carrier_timestamp IS NOT NULL
            AND so.order_delivered_customer_timestamp IS NOT NULL
        THEN DATE_DIFF('hour', so.order_delivered_carrier_timestamp, so.order_delivered_customer_timestamp)
    END AS hours_in_transit,

    -- Derived metrics: Delivery performance
    CASE
        WHEN so.order_delivered_customer_timestamp IS NOT NULL
        THEN DATE_DIFF('hour', so.order_delivered_customer_timestamp, so.order_estimated_delivery_date)
    END AS delivered_vs_estimated,

    CASE
        WHEN so.order_delivered_customer_timestamp IS NOT NULL
            AND so.order_delivered_customer_timestamp <= so.order_estimated_delivery_date
        THEN TRUE
        WHEN so.order_delivered_customer_timestamp IS NOT NULL
        THEN FALSE
    END AS delivered_on_time
    
FROM {{ ref("stg_orders")}} so

-- Join stg_customers to take customer_id
LEFT JOIN {{ ref("stg_customers") }} sc
    ON so.order_customer_id = sc.order_customer_id

-- Join dim_customers to replace order_customer_id by customer_key
LEFT JOIN {{ ref("dim_customers") }} c
    ON sc.customer_id = c.customer_id
    AND so.order_purchase_timestamp >= c.valid_from
    AND so.order_purchase_timestamp < c.valid_to

-- Order-item aggregates in order level
LEFT JOIN order_items_aggregates oi
    on so.order_id = oi.order_id

-- Order-payments aggregates in order level
LEFT JOIN order_payments_aggregates op
    ON so.order_id = op.order_id
