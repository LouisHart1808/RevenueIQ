select order_id, shipped_at,delivered_at,estimated_at,delivery_days,on_time from {{ ref('fact_orders') }}
