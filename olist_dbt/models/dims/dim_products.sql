{{ config(materialized='table') }}
WITH 
    product_order_details AS (
        SELECT
            p.product_id,
            oi.order_id,
            oi.seller_id,
            oi.price,
            o.order_purchase_timestamp
        FROM {{ ref("stg_products") }} p
        LEFT JOIN {{ ref("stg_order_items")}} oi
            ON p.product_id = oi.product_id
        LEFT JOIN {{ ref("stg_orders") }} o
            ON oi.order_id = o.order_id
    ),

    product_metrics AS (
        SELECT
            product_id,
            MIN(order_purchase_timestamp) AS first_order_date,
            MAX(order_purchase_timestamp) AS latest_order_date,
            COUNT(DISTINCT seller_id) AS unique_seller_count,
            COUNT(DISTINCT order_id) AS total_orders_containing_product,
            COUNT(*) AS total_unit_sold
        FROM product_order_details
        GROUP BY product_id
    ),

    product_price_metrics AS (
        SELECT
            product_id,
            MIN(price) AS min_price,
            MAX(price) AS max_price,
            AVG(price) AS avg_price,
            STDDEV(price) AS price_stddev,
            (STDDEV(price) / AVG(price) * 100) AS price_variation_coefficient,
            COUNT(DISTINCT price) AS distinct_price_count
        FROM product_order_details
        GROUP BY product_id
    )

SELECT
    {{ dbt_utils.generate_surrogate_key(['p.product_id']) }} AS product_key,

    -- Product identifiers
    p.product_id,

    -- Category attributes
    p.category_name_portuguese,
    pct.category_name_english,

    -- Product listing attributes
    p.name_length,
    p.description_length,
    p.photo_quantity,

    -- Physical dimensions
    p.weight_gram,
    p.length_cm,
    p.width_cm,
    p.height_cm,

    -- Physical metrics
    CASE
        WHEN p.weight_gram > 10000 THEN 'heavy'
        WHEN p.weight_gram > 5000 THEN 'medium'
        ELSE 'light'
    END AS weight_category,
    CASE
        WHEN (p.length_cm * p.width_cm * p.height_cm) > 100000 THEN 'large',
        WHEN (p.length_cm * p.width_cm * p.height_cm) > 10000 THEN 'medium',
        ELSE 'small'
    END AS size_category,

    -- Listing completeness
    CASE
        WHEN p.name_length > 0
            AND p.description_length > 0
            AND p.photo_quantity > 0
        THEN TRUE,
        ELSE FALSE
    END AS has_complete_listing,
    
    -- Historical reference
    pm.first_order_date,
    pm.unique_seller_count,
    pm.total_orders_containing_product,
    pm.total_unit_sold,

    -- Price metrics
    ppm.min_price,
    ppm.max_price,
    ppm.avg_price,
    ppm.price_variation_coefficient,

    -- Price variation classification
    CASE
        WHEN ppm.price_variation_coefficient IS NULL THEN 'no_sales'
        WHEN ppm.price_variation_coefficient > 50 THEN 'high_variation'
        WHEN ppm.price_variation_coefficient > 20 THEN 'moderate_variation'
        WHEN ppm.price_variation_coefficient > 0 THEN 'low_variation'
        ELSE 'fixed_price'
    END AS price_variation_category

FROM {{ ref('stg_products') }} p
LEFT JOIN product_metrics pm
    ON p.product_id = pm.product_id
LEFT JOIN product_price_metrics ppm
    ON p.product_id = ppm.product_id
LEFT JOIN {{ ref("stg_product_category_translation") }} pct
    ON p.category_name_portuguese = pct.category_name_portuguese
