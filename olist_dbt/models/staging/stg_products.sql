{{ config(materialized='view') }}

SELECT
    -- Unique identifier
    TRIM("product_id") AS product_id,

    -- Category reference
    TRIM("product_category_name") AS category_name_portuguese,
    
    -- Attributes: Remove redundant prefix 
    "product_name_lenght" AS name_length, -- Fixed typo from source
    "product_description_lenght" AS description_length, -- Fixed typo from source
    "product_photos_qty" AS photo_quantity,
    "product_weight_g" AS weight_gram,
    "product_length_cm" AS length_cm,
    "product_width_cm" AS width_cm,
    "product_height_cm" AS height_cm

FROM {{ source("raw", "raw_products") }}