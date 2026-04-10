{{ config(materialized = 'table') }}

WITH
  monthly_regional AS (
    SELECT 
      region,
      date_trunc(order_purchASe_timestamp, MONTH) AS purchase_month,
      COUNT(*) AS total_orders,
      SUM(CASE WHEN order_status = 'delivered' THEN 1 ELSE 0 END) AS total_delivered_orders,
      SUM(CASE WHEN order_status = 'delivered' and delivered_on_time = false THEN 1 ELSE 0 END) AS total_late_orders 
    FROM {{ ref("mart_order_fulfillment") }}
    GROUP BY region, purchase_month),
  monthly_all_region AS (
    SELECT
      'all_region' AS region,
      purchase_month,
      SUM(total_orders) AS total_orders,
      SUM(total_delivered_orders) AS total_delivered_orders,
      SUM(total_late_orders) AS total_late_orders
    FROM monthly_regional
    GROUP BY region, purchase_month
  ),
  combined AS (
    SELECT * FROM monthly_regional
    UNION ALL
    SELECT * FROM monthly_all_region
  ),
  baseline_month AS (
    SELECT min(purchase_month) AS baseline_month_value FROM (
      SELECT 
        purchase_month,
        COUNT(DISTINCT region) AS COUNT_region,
      FROM combined
      WHERE
        region != 'all_region'
            AND total_delivered_orders > 0
            AND total_late_orders > 0
      GROUP BY purchase_month
      HAVING COUNT(DISTINCT region) = (
        SELECT
          COUNT(DISTINCT region)
        FROM combined
        where region != 'all_region'
      )
    )),
  baseline AS (
    SELECT 
      DISTINCT c.region,
      bm.baseline_month_value
    FROM combined c
    CROSS JOIN baseline_month bm),
  baseline_value AS (
    SELECT
      c.region,
      c.total_orders AS baseline_total_orders,
      c.total_late_orders / NULLIF(c.total_delivered_orders, 0) AS baseline_late_delivery_rate
    FROM combined c
    INNER JOIN baseline b
      ON c.region = b.region
        AND c.purchase_month = b.baseline_month_value
  )
SELECT 
  c.region,
  CAST(c.purchase_month AS DATE) AS purchase_month_date_format,
  FORMAT_DATE('%Y-%m', c.purchase_month) AS purchase_month_year_format,
  c.total_orders,
  c.total_delivered_orders,
  c.total_late_orders,
  c.total_late_orders / NULLIF(c.total_delivered_orders, 0) AS late_delivery_rate,
  (c.total_orders / NULLIF(bv.baseline_total_orders, 0)) * 100 AS volume_indexed,
  (
    (c.total_late_orders / NULLIF(c.total_delivered_orders, 0)) /
    NULLIF(bv.baseline_late_delivery_rate, 0)
  ) * 100 AS late_delivery_rate_indexed,
  bv.baseline_late_delivery_rate
FROM combined c
INNER JOIN baseline_value bv
  ON c.region = bv.region