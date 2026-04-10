{{ config(materialized='table') }}

WITH 
    customer_orders AS (
    -- Join customers with orders to get order dates
        SELECT
            c.customer_id,
            c.zip_code_prefix,
            c.city,
            c.state,
            o.order_id,
            o.order_purchase_timestamp
        FROM {{ ref("stg_customers") }} c
        LEFT JOIN {{ ref("stg_orders") }} o
            ON c.order_customer_id = o.order_customer_id
    ),

    customer_addresses AS (
    -- Get unique customer-address combinations
        SELECT
            customer_id,
            zip_code_prefix,
            city,
            state,
            MIN(order_purchase_timestamp) as first_seen_date
        FROM customer_orders
        GROUP BY
            customer_id,
            zip_code_prefix,
            city,
            state
    ),

    customer_address_history AS (
    -- Adding validity periods
        SELECT
            customer_id,
            zip_code_prefix,
            city,
            state,
            first_seen_date,
            ROW_NUMBER() OVER(PARTITION BY customer_id ORDER BY first_seen_date) AS address_sequence,
            LEAD(first_seen_date) OVER(PARTITION BY customer_id ORDER BY first_seen_date) AS next_address_date
        FROM customer_addresses
    )
    
-- Final dimension with validity periods and customer metrics 
SELECT
    {{ dbt_utils.generate_surrogate_key(['cah.customer_id','cah.address_sequence']) }} AS customer_key,

    -- Customer identifiers
    cah.customer_id,
    
    -- Address attributes
    cah.zip_code_prefix,
    cah.city,
    cah.state,
    
    -- Geographic classification
    CASE 
        WHEN cah.state IN ('SP', 'RJ', 'MG', 'ES') THEN 'Southeast'
        WHEN cah.state IN ('RS', 'SC', 'PR') THEN 'South'
        WHEN cah.state IN ('BA', 'SE', 'AL', 'PE', 'PB', 'RN', 'CE', 'PI', 'MA') THEN 'Northeast'
        WHEN cah.state IN ('GO', 'MT', 'MS', 'DF') THEN 'Central West'
        WHEN cah.state IN ('AM', 'RR', 'AP', 'PA', 'TO', 'RO', 'AC') THEN 'North'
    END AS region,

    -- Validity periods
    cah.first_seen_date AS valid_from,
    COALESCE(cah.next_address_date, CAST('9999-12-31 23:59:59' AS TIMESTAMP)) AS valid_to,
    CASE
        WHEN cah.next_address_date IS NULL THEN TRUE
        ELSE FALSE
    END AS is_current,

    -- Metadata for tracking data freshness
    CURRENT_TIMESTAMP AS updated_at

FROM customer_address_history cah