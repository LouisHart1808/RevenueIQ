with months as (
 select date_trunc('month',o.purchase_date)::date as month,i.category,sum(i.price) as sales
 from warehouse.fact_orders o join warehouse.fact_order_items i using(order_id)
 where o.order_status='delivered' group by 1,2
), comparison as (
 select a.*,b.sales as previous_sales from months a left join months b
 on a.category=b.category and a.month=b.month+interval '1 month'
)
select *,sales/nullif(previous_sales,0)-1 as mom_growth from comparison order by month, sales desc;
