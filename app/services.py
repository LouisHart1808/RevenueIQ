"""Parameterized PostgreSQL queries; filters select whole orders via EXISTS."""

import os
from functools import lru_cache
import pandas as pd
from sqlalchemy import create_engine, text
from app.releases import current_release, pinned_release, identifier
from app.customers import customer_cte, cohort_sql
from app.filters import predicate

ENGINE = create_engine(
    os.getenv("DATABASE_URL", "postgresql+psycopg2://localhost:55432/revenueiq"),
    pool_pre_ping=True,
    connect_args={"options": "-c statement_timeout=30000"},
)


def query(sql, params=None):
    with ENGINE.connect() as conn:
        schema = identifier(current_release(ENGINE))
        return pd.read_sql(text(sql.replace("warehouse.", schema + ".")), conn, params=params or {})


@lru_cache(maxsize=64)
def snapshot(start=None, end=None, state=None, category=None, seller=None, release="warehouse"):
    where, params = predicate(start, end, state, category, seller)
    base = f"from warehouse.fact_orders o where {where}"
    eligible = base + " and o.order_status='delivered'"
    params["as_of"] = end
    out = {}
    out["kpi"] = query(
        f"""select count(*) as orders,count(distinct customer_unique_id) as customers,coalesce(sum(sales),0) as sales,avg(sales) as aov,avg(on_time::int) as on_time,sum(freight) as freight,sum(payment_total) as payments {eligible}""",
        params,
    )
    out["monthly"] = query(
        f"select date_trunc('month',purchase_date)::date as month,sum(sales) as sales,count(*) as orders,count(distinct customer_unique_id) as customers,avg(sales) as aov {eligible} group by 1 order by 1",
        params,
    )
    out["categories"] = query(
        f"select i.category,sum(i.price) as sales,count(*) as units,count(distinct i.order_id) as orders from warehouse.fact_order_items i join warehouse.fact_orders o using(order_id) where {where} and o.order_status='delivered' group by 1 order by 2 desc",
        params,
    )
    products_sql, products_params = product_query(start, end, state, category, seller)
    out["products"] = query(products_sql + product_order("sales") + " limit 200", products_params)
    out["regions"] = query(
        f"select state,sum(sales) as sales,count(*) as orders,avg(sales) as aov,avg(on_time::int) as on_time,avg(delivery_days) as delivery_days {eligible} group by 1 order by 2 desc",
        params,
    )
    out["segments"] = query(
        customer_cte()
        + f"select c.segment,count(distinct o.customer_unique_id) as customers,sum(o.sales) as sales,count(*) as orders from history o join customer_asof c using(customer_unique_id) where {where} and o.order_status='delivered' group by 1 order by 3 desc",
        params,
    )
    out["repeat"] = query(
        f"select avg((n>1)::int) as rate from (select customer_unique_id,count(*) as n {eligible} group by 1) x", params
    )
    out["sellers"] = query(
        f"select i.seller_id,sum(i.price) as sales,count(distinct o.order_id) as orders,avg(o.on_time::int) as on_time from (select order_id,seller_id,sum(price) as price from warehouse.fact_order_items group by 1,2) i join warehouse.fact_orders o using(order_id) where {where} and o.order_status='delivered' group by 1 order by 2 desc limit 100",
        params,
    )
    out["operations"] = query(
        f"select coalesce(on_time::text,'Unknown') as on_time,count(*) as orders,avg(review_score) as review_score,avg(delivery_days) as delivery_days,percentile_cont(0.5) within group(order by delivery_days) as median_days,percentile_cont(0.9) within group(order by delivery_days) as p90_days {eligible} group by 1",
        params,
    )
    out["operations"]["on_time"] = out["operations"]["on_time"].replace({"true": "On time", "false": "Late"})
    out["status"] = query(f"select order_status,count(*) as orders {base} group by 1", params)
    out["acquisition"] = query(
        customer_cte()
        + f"select date_trunc('month',o.purchase_date)::date as month,count(distinct o.customer_unique_id) filter(where date_trunc('month',o.purchase_date)=date_trunc('month',c.first_purchase)) as new_customers,count(distinct o.customer_unique_id) filter(where date_trunc('month',o.purchase_date)>date_trunc('month',c.first_purchase)) as returning_customers from history o join customer_asof c using(customer_unique_id) where {where} and o.order_status='delivered' group by 1 order by 1",
        params,
    )
    out["distribution"] = query(
        customer_cte()
        + f"select c.frequency,count(distinct c.customer_unique_id) as customers from history o join customer_asof c using(customer_unique_id) where {where} and o.order_status='delivered' group by 1 order by 1",
        params,
    )
    out["operations_monthly"] = query(
        f"select date_trunc('month',purchase_date)::date as month,avg(delivery_days) as delivery_days,avg(on_time::int) as on_time,avg(review_score) as review_score {eligible} group by 1 order by 1",
        params,
    )
    out["reviews"] = query(
        f"select round(review_score::numeric,0) as score,count(*) as orders {eligible} and review_score is not null group by 1 order by 1",
        params,
    )
    out["category_monthly"] = query(
        f"select date_trunc('month',o.purchase_date)::date as month,i.category,sum(i.price) as sales from warehouse.fact_order_items i join warehouse.fact_orders o using(order_id) where {where} and o.order_status='delivered' group by 1,2 order by 1,2",
        params,
    )
    out["value_distribution"] = query(
        customer_cte()
        + f"select (floor(c.monetary/100)*100)::int as monetary_bucket,count(distinct c.customer_unique_id) as customers from history o join customer_asof c using(customer_unique_id) where {where} and o.order_status='delivered' group by 1 order by 1",
        params,
    )
    out["recency_distribution"] = query(
        customer_cte()
        + f"select (floor(c.recency/30)*30)::int as recency_bucket,count(distinct c.customer_unique_id) as customers from history o join customer_asof c using(customer_unique_id) where {where} and o.order_status='delivered' group by 1 order by 1",
        params,
    )
    out["category_quality"] = query(
        f"select c.category,count(*) as orders,avg(o.on_time::int) as on_time,avg(o.review_score) as review_score from (select distinct order_id,category from warehouse.fact_order_items) c join warehouse.fact_orders o using(order_id) where {where} and o.order_status='delivered' group by 1 having count(*)>=30 order by 2 desc",
        params,
    )
    out["cohorts"] = query(cohort_sql(where), params)
    out["segment_detail"] = query(
        customer_cte()
        + f"select c.segment,count(distinct c.customer_unique_id) as customers,avg(c.recency) as mean_recency_days,avg(c.frequency) as frequency,avg(c.monetary) as historical_value from customer_asof c where exists(select 1 from history o where o.customer_unique_id=c.customer_unique_id and {where}) group by 1",
        params,
    )
    out["customer_boundary"] = query(customer_cte() + "select cutoff from boundary", params)
    return out


@pinned_release
def get_snapshot(*args):
    return snapshot(*args, release=current_release(ENGINE))


def product_query(start=None, end=None, state=None, category=None, seller=None, search=None):
    """One aggregation shared by browsing, counting, and complete CSV exports."""
    where, params = predicate(start, end, state, category, seller)
    if search and search.strip():
        # Escape LIKE wildcards so user input is a literal substring.
        term = search.strip().replace("!", "!!").replace("%", "!%").replace("_", "!_")
        params["product_search"] = "%" + term + "%"
        where += " and (i.product_id ilike :product_search escape '!' or i.category ilike :product_search escape '!')"
    return (
        "select i.category,i.product_id,sum(i.price) as sales,count(*) as units,avg(i.price) as average_price "
        "from warehouse.fact_order_items i join warehouse.fact_orders o using(order_id) "
        f"where {where} and o.order_status='delivered' group by 1,2",
        params,
    )


def product_order(sort):
    # SQL identifiers are never interpolated from untrusted input.
    column = sort if sort in {"sales", "units", "average_price", "category"} else "sales"
    direction = "asc" if column == "category" else "desc"
    return f" order by {column} {direction}, product_id asc"


def product_page(
    page=0, page_size=20, start=None, end=None, state=None, category=None, seller=None, *, search=None, sort="sales"
):
    sql, params = product_query(start, end, state, category, seller, search)
    page_size = max(1, min(int(page_size), 100))
    params.update({"limit": page_size, "offset": max(0, int(page)) * page_size})
    return query(sql + product_order(sort) + " limit :limit offset :offset", params)


def product_count(start=None, end=None, state=None, category=None, seller=None, *, search=None):
    sql, params = product_query(start, end, state, category, seller, search)
    return int(query("select count(*) as total from (" + sql + ") products", params).iloc[0].total)


def export_products(start=None, end=None, state=None, category=None, seller=None, *, search=None, sort="sales"):
    sql, params = product_query(start, end, state, category, seller, search)
    return query(sql + product_order(sort), params)
