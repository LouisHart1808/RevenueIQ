with base as (
    select o.customer_unique_id, o.sales,
        date_trunc('month', o.purchase_date)::date as month,
        date_trunc('month', c.first_purchase)::date as cohort
    from {{ ref('fact_orders') }} o
    join {{ ref('mart_customer') }} c using (customer_unique_id)
    where o.order_status = 'delivered'
), sizes as (
    select cohort, count(distinct customer_unique_id) as acquired from base group by 1
), active as (
    select cohort,
        (extract(year from age(month, cohort))*12 + extract(month from age(month, cohort)))::int as age,
        count(distinct customer_unique_id) as customers, sum(sales) as sales
    from base group by 1, 2
), observed as (
    select s.cohort, g.age, s.acquired,
        coalesce(a.customers, 0) as customers,
        coalesce(a.customers, 0)::float / s.acquired as retention,
        coalesce(a.sales, 0) as sales
    from sizes s
    cross join lateral generate_series(0,
        (extract(year from age((select max(month) from base), s.cohort))*12
        + extract(month from age((select max(month) from base), s.cohort)))::int
    ) g(age)
    left join active a on s.cohort = a.cohort and g.age = a.age
)
select *,
    sum(sales) over (partition by cohort order by age) as cumulative_sales,
    sum(sales) over (partition by cohort order by age) / acquired as cumulative_value_per_customer
from observed
