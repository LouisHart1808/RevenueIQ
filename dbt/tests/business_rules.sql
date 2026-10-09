select 'negative_sales' as failure where exists(select 1 from {{ ref('fact_orders') }} where sales<0 or freight<0)
union all select 'missing_customers' where exists(select 1 from {{ ref('fact_orders') }} where customer_unique_id is null)
union all select 'category_reconciliation' where abs((select sum(sales) from {{ ref('mart_category') }})-(select sum(sales) from {{ ref('mart_revenue') }}))>.01
union all select 'future_cohort' where exists(select 1 from {{ ref('mart_cohort') }} where cohort+age*interval '1 month'>(select max(date_trunc('month',purchase_date)) from {{ ref('fact_orders') }} where order_status='delivered'))
union all select 'item_keys' where exists(select order_id,order_item_id from {{ ref('fact_order_items') }} group by 1,2 having count(*)>1)
union all select 'payment_keys' where exists(select order_id,payment_sequential from {{ ref('fact_payments') }} group by 1,2 having count(*)>1)
union all select 'cohort_origin' where exists(select 1 from {{ ref('mart_cohort') }} where age=0 and retention<>1)
union all select 'cohort_value' where abs((select sum(sales) from {{ ref('mart_cohort') }})-(select sum(sales) from {{ ref('mart_revenue') }}))>.01
