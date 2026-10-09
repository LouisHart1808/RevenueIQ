select 'sales' as failure where abs((select sum(sales) from {{ ref('fact_orders') }})-(select sum(price) from {{ ref('fact_order_items') }}))>0.01
union all select 'payments' where abs((select sum(payment_total) from {{ ref('fact_orders') }})-(select sum(payment_value) from {{ ref('fact_payments') }}))>0.01
union all select 'orders' where (select count(*) from {{ ref('fact_orders') }})<>(select count(*) from {{ ref('stg_orders') }})
union all select 'cohort' where exists(select 1 from {{ ref('mart_cohort') }} where retention<0 or retention>1)
