{{ config(materialized='view') }}

SELECT
    CAST(product_category_name AS STRING) AS category_name_portuguese,
    TRIM(product_category_name_english) AS category_name_english

FROM {{ source("raw", "product_category_name_translation") }}