{{ config(materialized='view') }}

SELECT
    TRIM("product_category_name") AS category_name_portuguese,
    TRIM("product_category_name_english") AS category_name_english

FROM {{ source("raw", "raw_product_category_name_translation") }}