-- Delivered merchandise, grouped on purchase date. Never join payments to raw items.
select purchase_date, sum(sales) as daily_sales from warehouse.fact_orders where order_status='delivered' group by 1 order by 1;
select date_trunc('week',purchase_date) as week, sum(sales) as weekly_sales from warehouse.fact_orders where order_status='delivered' group by 1 order by 1;
select date_trunc('quarter',purchase_date) as quarter, sum(sales) as quarterly_sales from warehouse.fact_orders where order_status='delivered' group by 1 order by 1;
