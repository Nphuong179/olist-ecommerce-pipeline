{{ config(materialized='view') }}

SELECT
    TRIM("seller_id") AS seller_id,
    TRIM("seller_zip_code_prefix") AS zip_code_prefix,
    TRIM("seller_city") AS city,
    TRIM("seller_state") AS state

FROM {{ source("raw", "raw_sellers") }}