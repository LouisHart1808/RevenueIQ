"""Date-aware customer SQL. No purchases/deliveries after the cutoff enter features."""


def customer_cte():
    return """with boundary as (
      select least(coalesce(cast(:as_of as date),max(purchase_date)),max(purchase_date)) as cutoff
      from warehouse.fact_orders
    ), history as not materialized (
      select o.* from warehouse.fact_orders o cross join boundary b
      where o.order_status='delivered' and o.purchase_date<=b.cutoff
        and o.delivered_at < b.cutoff+interval '1 day'
    ), features as (
      select customer_unique_id,min(purchase_date) as first_purchase,max(purchase_date) as last_purchase,
        count(*) as frequency,sum(sales) as monetary
      from history group by 1
    ), recency as (
      select f.*,b.cutoff+1-f.last_purchase as recency from features f cross join boundary b
    ), customer_asof as (
      select *,case when recency<=90 and frequency>=3 then 'Champions'
        when recency<=180 and frequency>=2 then 'Loyal Customers'
        when recency<=30 then 'New Customers' when recency<=90 then 'Potential Loyalists'
        when recency<=180 then 'At-Risk Customers' else 'Inactive Customers' end as segment
      from recency
    ) """


def cohort_sql(where):
    return (
        customer_cte()
        + f""", members as (
      select distinct c.customer_unique_id,date_trunc('month',c.first_purchase)::date as cohort
      from customer_asof c join history o on c.customer_unique_id=o.customer_unique_id
      and c.first_purchase=o.purchase_date where {where}
    ), sizes as (
      select cohort,count(*) as acquired from members group by 1
    ), active as (
      select m.cohort,(extract(year from age(date_trunc('month',o.purchase_date),m.cohort))*12+
        extract(month from age(date_trunc('month',o.purchase_date),m.cohort)))::int as age,
        count(distinct m.customer_unique_id) as customers,sum(o.sales) as sales
      from members m join history o using(customer_unique_id) group by 1,2
    ), observed as (
      select s.cohort,g.age,s.acquired,coalesce(a.customers,0) as customers,
        coalesce(a.customers,0)::float/s.acquired as retention,coalesce(a.sales,0) as sales,
        (s.cohort+(g.age+1)*interval '1 month'-interval '1 day')::date > b.cutoff as partial_month
      from sizes s cross join boundary b
      cross join lateral generate_series(0,(extract(year from age(date_trunc('month',b.cutoff),s.cohort))*12+
        extract(month from age(date_trunc('month',b.cutoff),s.cohort)))::int) g(age)
      left join active a on s.cohort=a.cohort and g.age=a.age
    ) select *,sum(sales) over(partition by cohort order by age)/acquired as cumulative_value_per_customer
    from observed order by cohort,age"""
    )
