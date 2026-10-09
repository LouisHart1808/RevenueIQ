### Metric contract
All amounts are nominal Brazilian reais (BRL). Purchase date is the date basis. Main sales KPIs include **delivered** orders only; canceled, unavailable, and in-flight orders are excluded. No recognized revenue or profit is available.

| Metric | Calculation | Grain / exclusions |
|---|---|---|
| Merchandise sales / GMV proxy | `sum(fact_orders.sales)` = eligible `sum(fact_order_items.price)` | Order / excludes freight; GMV definition varies by business |
| Shipping charges | `sum(freight)` | Order / delivered only |
| Payment totals | `sum(payment_total)` | Preaggregated order / includes payment components; not net revenue |
| AOV | `sum(sales)/count(*)` | Delivered order / merchandise only |
| Purchasing customers | `count(distinct customer_unique_id)` | Persistent identity, never order-specific customer_id |
| Repeat purchase rate | Customers with ≥2 selected orders / selected customers | Delivered orders inside selection |
| Frequency | Orders / purchasing customers | Same eligible population |
| On-time rate | `avg(on_time::int)` | Delivered orders with actual + estimated delivery date; day-level comparison |
| Cancellation rate | Canceled orders / all orders | All statuses, purchase-date basis |
| Review score | Mean of reviews per order, then mean over orders | Missing reviews excluded |
| Historical customer value | Sum of delivered merchandise sales | History through selected cutoff; known deliveries only, not profit or predictive CLV |
| Cohort retention | Distinct active customers / original acquired customers | Filtered acquisition cohort; followed through cutoff; future cells absent |
| RFM | Recency days, order frequency, sales sum | Reference: selected cutoff + 1 day, capped at source coverage |

RFM rules, in priority order: Champions (recency ≤90 days, frequency ≥3); Loyal (≤180 days, ≥2); New (≤30 days); Potential Loyalists (≤90 days); At-Risk (≤180 days); Inactive (older). These are documented heuristic labels, not learned churn predictions. "New" means recent low-frequency activity under this rule, not a verified current acquisition event.

**Filter semantics:** date, state, and category select whole orders. A category filter means the basket contains that category; its KPI includes all merchandise in those baskets. Category breakdowns partition those same baskets and reconcile. Customer labels and distributions use known deliveries through the selected cutoff. Cohorts apply filters to acquisition orders, then follow the original members across all subsequent purchases through the cutoff. Research modules retain their explicitly defined development/test populations, independent of global filters. Source dates have no trustworthy timezone annotation and are retained as local naive timestamps.

**Unsupported:** costs, margins, profit, CAC, ROAS, marketing attribution, refund-adjusted net revenue, and defensible predictive CLV. Scenarios use explicit user assumptions only. Dates in 2016 launch and the terminal extraction period should not be used for unqualified growth comparisons.

Additional metric contracts:

|Metric|SQL or calculation|Grain, status, date and limits|
|---|---|---|
|New customers|Distinct persistent IDs where purchase month = first delivered purchase month|Delivered orders; purchase date; first observed acquisition only|
|Returning customers|Distinct IDs where purchase month > first delivered month|A customer is classified by month, not their within-month order sequence|
|Units sold|`count(*)` in eligible items|One item row represents one unit; no quantity column inferred|
|Average item price|`sum(price)/count(*)`|Delivered item; purchase-date selection; no discounts inferred|
|Category share|Category item sales / total eligible item sales|Eligible whole baskets partitioned by item category|
|Revenue per customer|`sum(sales)/count(distinct customer_unique_id)`|Same delivered selection and purchase date|
|Delivery duration|Actual delivery timestamp − purchase timestamp, days|Delivered orders with dates; missing values excluded|
|Delay|Actual delivery date − estimated date|Calendar days; positive means late|
|Pair support|Orders containing both products / delivered baskets|Full history; distinct product set per order|
|Pair confidence|Orders containing both / orders containing antecedent|Full history; minimum 20 co-purchases|
|Pair lift|Confidence / consequent prevalence|Exploratory; sparse pairs and multiple testing limit actionability|
|MoM growth|Current month sales / prior calendar month sales − 1|Complete selected months only; launch/terminal context remains important|
|Decomposition|Shapley allocation across customers × frequency × AOV|Exact allocation, not causal attribution; complete conservative window|
|Scenario value|Baseline × (1+customer change) × (1+frequency change) × (1+AOV change)|User assumptions, not observed uplift or profit|

Customer histories require actual delivery by the cutoff; unknown/future deliveries are excluded even when the final dataset marks an order delivered. Revenue KPIs remain retrospective final-status measures. Consequently, as-of segment totals can differ from revenue KPIs; this is an explicit population distinction, not a join discrepancy.
