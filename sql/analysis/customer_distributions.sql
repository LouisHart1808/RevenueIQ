select frequency,count(*) as customers,sum(monetary) as sales from warehouse.mart_customer group by 1 order by 1;
select segment,count(*) as customers,avg(recency) as mean_recency,avg(frequency) as frequency,avg(monetary) as historical_value,sum(monetary)/sum(frequency) as aov from warehouse.mart_customer group by 1;
