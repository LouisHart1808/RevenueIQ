select date_trunc('month',purchase_date)::date as month,state,count(*) as orders,
 avg(on_time::int) as on_time_rate,avg(delivery_days) as delivery_days,
 percentile_cont(0.5) within group(order by delivery_days) as median_days,
 percentile_cont(0.9) within group(order by delivery_days) as p90_days,
 avg(review_score) as review_score
from {{ ref('fact_orders') }} where order_status='delivered' group by 1,2
