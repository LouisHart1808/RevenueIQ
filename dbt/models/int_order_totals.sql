select order_id, sum(price)::numeric(18,2) as sales, sum(freight_value)::numeric(18,2) as freight, count(*) as units from {{ ref('fact_order_items') }} group by 1
