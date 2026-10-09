select state,count(*) as orders,avg(on_time::int) as on_time_rate,
 percentile_cont(0.5) within group(order by delivery_days) as median_days,
 percentile_cont(0.9) within group(order by delivery_days) as p90_days,
 avg(review_score) as review_score
from warehouse.fact_orders where order_status='delivered' group by 1;
select count(*) filter(where order_status='canceled')::numeric/count(*) as cancellation_rate from warehouse.fact_orders;
