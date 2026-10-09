select date_trunc('month',o.purchase_date)::date as month,i.category,
 sum(i.price) as sales,count(*) as units,count(distinct o.order_id) as orders,
 avg(i.price) as average_price
from {{ ref('fact_orders') }} o join {{ ref('fact_order_items') }} i using(order_id)
where o.order_status='delivered' group by 1,2
