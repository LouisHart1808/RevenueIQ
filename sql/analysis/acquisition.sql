-- Customer is new only in their first observed delivered month. History is left-censored.
select date_trunc('month',o.purchase_date)::date as month,
 count(distinct o.customer_unique_id) filter(where date_trunc('month',o.purchase_date)=date_trunc('month',c.first_purchase)) as new_customers,
 count(distinct o.customer_unique_id) filter(where date_trunc('month',o.purchase_date)>date_trunc('month',c.first_purchase)) as returning_customers,
 sum(o.sales) filter(where date_trunc('month',o.purchase_date)=date_trunc('month',c.first_purchase)) as new_customer_sales,
 sum(o.sales) filter(where date_trunc('month',o.purchase_date)>date_trunc('month',c.first_purchase)) as returning_customer_sales
from warehouse.fact_orders o join warehouse.mart_customer c using(customer_unique_id)
where o.order_status='delivered' group by 1 order by 1;
