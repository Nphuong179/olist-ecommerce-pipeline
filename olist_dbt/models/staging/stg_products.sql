{{ config(materialized='view') }}

SELECT
    TRIM("product_id") AS product_id,
    TRIM("product_category_name") AS category_name_portuguese,
    "product_name_lenght" AS product_name_length, -- Fixed typo from source
    "product_description_lenght" AS product_description_length, -- Fixed typo from source
    "product_photos_qty" AS product_photo_quantity,
    "product_weight_g" AS product_weight_gram,
    "product_length_cm" AS product_length_cm,
    "product_width_cm" AS product_width_cm

FROM {{ source("raw", "raw_products") }}