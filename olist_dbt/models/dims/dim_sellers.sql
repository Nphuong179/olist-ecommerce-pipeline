{{ config(materialized='table') }}

WITH 
    seller_orders AS (
    -- Join sellers with orders to get order dates
        SELECT
            s.seller_id,
            s.zip_code_prefix,
            s.city,
            s.state,
            o.order_purchase_timestamp
        FROM {{ ref("stg_sellers") }} s
        LEFT JOIN {{ ref("stg_order_items") }} oi
            ON s.seller_id = oi.seller_id
        LEFT JOIN {{ ref("stg_orders") }} o
            ON oi.order_id = o.order_id
    ),

    seller_addresses AS (
    -- Get unique seller-address combinations
        SELECT
            seller_id,
            zip_code_prefix,
            city,
            state,
            MIN(order_purchase_timestamp) AS first_seen_date
        FROM seller_orders
        GROUP BY
            seller_id,
            zip_code_prefix,
            city,
            state
    ),

    seller_address_history AS (
    -- Adding validity periods
        SELECT
            *,
            ROW_NUMBER() OVER(PARTITION BY seller_id ORDER BY first_seen_date) AS address_sequence,
            LEAD(first_seen_date) OVER(PARTITION BY seller_id ORDER BY first_seen_date) AS next_address_date
        FROM seller_addresses
    ),

    seller_metrics AS (
        SELECT
            seller_id,
            MIN(order_purchase_timestamp) AS first_order_date,
            MAX(order_purchase_timestamp) AS last_order_date
        FROM seller_orders
        GROUP BY seller_id
    )

    -- Final dimension with validity periods and seller metrics
SELECT 
    {{ dbt_utils.generate_surrogate_key(['sah.seller_id','sah.address_sequence']) }} AS seller_key,

    -- Seller identifier
    sah.seller_id,

    -- Address attributes
    sah.zip_code_prefix,
    sah.city,
    sah.state,

    -- Geographic classification
    CASE 
        WHEN sah.state IN ('SP', 'RJ', 'MG', 'ES') THEN 'southeast'
        WHEN sah.state IN ('RS', 'SC', 'PR') THEN 'south'
        WHEN sah.state IN ('BA', 'SE', 'AL', 'PE', 'PB', 'RN', 'CE', 'PI', 'MA') THEN 'northeast'
        WHEN sah.state IN ('GO', 'MT', 'MS', 'DF') THEN 'central_west'
        WHEN sah.state IN ('AM', 'RR', 'AP', 'PA', 'TO', 'RO', 'AC') THEN 'north'
    END AS region,

    -- Seller_metrics
    sm.first_order_date,
    sm.last_order_date,

    -- Validity periods
    sah.first_seen_date AS valid_from,
    COALESCE(sah.next_address_date, CAST('9999-12-31 23:59:59' AS TIMESTAMP)) AS valid_to,
    CASE 
        WHEN next_address_date IS NULL THEN TRUE
        ELSE FALSE
    END AS is_current,

    -- Metadata for tracking data freshness
    CURRENT_TIMESTAMP AS updated_at

FROM seller_address_history sah
LEFT JOIN seller_metrics sm
    ON sah.seller_id = sm.seller_id