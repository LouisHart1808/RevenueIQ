{{ config(indexes=[{'columns':['order_id'],'unique':true},{'columns':['purchase_date']},{'columns':['customer_unique_id']}]) }}
with payments as (select order_id,sum(payment_value)::numeric(18,2) as payment_total from {{ ref('fact_payments') }} group by 1), reviews as (select order_id,avg(review_score) as review_score from {{ ref('fact_reviews') }} group by 1)
select o.order_id,o.order_status,c.customer_unique_id,c.state,c.city,
o.order_purchase_timestamp::timestamp as purchased_at,o.order_purchase_timestamp::timestamp::date as purchase_date,
o.order_approved_at::timestamp as approved_at,o.order_delivered_carrier_date::timestamp as shipped_at,
o.order_delivered_customer_date::timestamp as delivered_at,o.order_estimated_delivery_date::timestamp as estimated_at,
coalesce(i.sales,0) as sales,coalesce(i.freight,0) as freight,coalesce(i.units,0) as units,p.payment_total,r.review_score,
extract(epoch from(o.order_delivered_customer_date::timestamp-o.order_purchase_timestamp::timestamp))/86400.0 as delivery_days,
case when o.order_status='delivered' and o.order_delivered_customer_date is not null and o.order_estimated_delivery_date is not null then o.order_delivered_customer_date::timestamp::date <= o.order_estimated_delivery_date::timestamp::date end as on_time
from {{ ref('stg_orders') }} o left join {{ ref('dim_customers') }} c using(customer_id) left join {{ ref('int_order_totals') }} i using(order_id) left join payments p using(order_id) left join reviews r using(order_id)
