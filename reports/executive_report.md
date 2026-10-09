# RevenueIQ — Executive business report

Historical Olist marketplace sample • BRL • delivered-order merchandise value • generated from PostgreSQL.

## Executive summary
The observed delivered population contains 96,478 orders from 93,358 persistent purchasing customers. Merchandise sales total R$ 13,221,498.11; average order value is R$ 137.04. This is transaction value, not Olist revenue, net revenue, or profit. Repeat purchase rate across the observed window is 3.00%. On-time delivery is 93.23% among eligible delivered orders with actual and estimated dates.

## Commercial performance
The largest category is health_beauty, with R$ 1,233,131.72 (9.33% of merchandise value). The largest state is SP, with R$ 5,067,633.16 (38.33%). See [monthly results](monthly.csv), [category results](categories.csv), and [regional results](regions.csv). Growth is descriptive; the launch period and terminal extraction tail cannot support clean annual seasonality claims.

## Customers
Repeat purchasing is sparse (3.00%), making predictive customer lifetime value unreliable without additional history. Use observed monetary value and rule-based RFM as descriptions of this sample. The application rebuilds customer labels from known deliveries by the selected date; no later purchases or deliveries enter those features. These report tables use the full available cutoff, never today's customer status. Cohort ages beyond the observable window are absent, not zero. Recommendations should be tested against newer, longer customer histories.

## Delivery and satisfaction
Late reviewed orders: 6,381; on-time reviewed orders: 89,443. Mean review difference (late minus on-time): -2.019 points; bootstrap 95% interval [-2.058, -1.976]. Two-sided Mann–Whitney p=Below floating-point precision; rank-biserial effect -0.638. The null is equal score distributions; the alternative is a distributional difference. Reviews are averaged within order. Bootstrap resamples orders with seed 42, assuming independent orders; seller/customer clustering and nonresponse may bias uncertainty. This observational association cannot establish that delivery improvements cause better ratings or more sales.

## Forecasting
This retrospective exercise uses January 2017–July 2018, excludes the sparse launch period and terminal tail, and compares last-month, three-month mean, seasonal-naive, and damped-trend forecasts with expanding chronological backtests. Selected model: Damped trend; development folds: 4. May–July 2018 are withheld from model selection and interval calibration. The fixed method is evaluated with expanding one-step forecasts; prior test observations become available only for later forecasts. Holdout MAE: R$ 133,227.85; WAPE: 14.79%; empirical interval coverage: 33.3% across 3 test months. Metrics are in [analytics.json](analytics.json). This dataset was explored in v1, so this is retrospective locked evaluation, not never-viewed external data. The 95% band uses frozen development errors; the small sample cannot establish nominal coverage. No present-day sales forecast is claimed.

## Prioritized recommendations
|Priority / finding|Evidence|Action and implication|Assumption-based impact|Confidence and validation|
|---|---|---|---|---|
|1. Investigate late deliveries|Review-score difference and interval above|Audit high-volume sellers and shipping lanes before intervention|No causal sales estimate supported|Moderate association evidence; run a randomized or phased operational trial, tracking ratings and lateness|
|2. Validate retention opportunity|Observed repeat rate 3.00%|Collect longer customer histories, then test relevant replenishment reminders|A hypothetical 3% frequency uplift at constant customers and AOV implies R$ 396,644.94 additional merchandise value|Low confidence in uplift assumption; use a holdout experiment and measure incremental orders|
|3. Examine leading category concentration|health_beauty contributes 9.33%|Review capacity, assortment, and seller reliability in this category|No profit impact can be sized without cost data|High confidence in historical share; validate demand and margins with current records|

## Product affinity
3,197 of 96,478 delivered baskets contain distinct products. Candidates require at least 20 co-purchases before January 2018. All candidates are evaluated on subsequent baskets, with BH multiple-testing correction across unique pairs. Replication requires at least 5 test co-purchases, lift above 1 and q ≤0.05; 0 of 1 candidates meet that rule. Dependence and changing assortment remain limitations; do not launch campaigns on this evidence alone.

## Limitations
Historical anonymized sample, unknown marketplace sampling completeness, sparse repeats, no cost/marketing/refund ledger, and possible review-selection bias. Paid totals, shipping, and merchandise differ legitimately. Actual delivery timestamps determine punctuality at calendar-day precision. Geographic displays use aggregate state coordinates and do not reveal customer addresses. Customer features stop at the selected cutoff and include only orders known delivered by it. Unknown delivery dates are excluded from those features. Other revenue views remain retrospective final-status merchandise measures. Source attribution: Olist, Brazilian E-Commerce Public Dataset, Kaggle, CC BY-NC-SA 4.0. Analytical outputs inherit applicable source-license obligations; code is separately licensed.

## Dependence-aware delivery evidence

On 94,563 single-seller reviewed orders, the mean difference is -2.038 points; two-way customer/seller clustered 95% interval [-2.086, -1.990]. This uses 91,622 customer clusters and 2,944 seller clusters, finite-sample covariance correction and a normal critical value. Multi-seller orders are excluded from this sensitivity analysis to avoid assigning a shared outcome to one arbitrary seller. Confounding and review nonresponse remain.

## Locked forecast test metrics

|    MAE |   RMSE |   WAPE |   sMAPE |
|-------:|-------:|-------:|--------:|
| 133228 | 142055 | 0.1479 |  0.1393 |

## Development-only model comparison

| Model            |      MAE |     RMSE |   WAPE |   sMAPE |
|:-----------------|---------:|---------:|-------:|--------:|
| Last month       | 110979   | 128069   | 0.1207 |  0.1291 |
| Three month mean |  97511.5 | 103864   | 0.106  |  0.1107 |
| Seasonal naive   | 658021   | 664262   | 0.7156 |  1.1384 |
| Damped trend     |  50858.7 |  67883.8 | 0.0553 |  0.0561 |

## Customer segment evidence

| segment             |   customers |            sales |   orders |
|:--------------------|------------:|-----------------:|---------:|
| Inactive Customers  |       66150 |      9.28809e+06 |    68230 |
| At-Risk Customers   |       17468 |      2.49258e+06 |    17468 |
| Potential Loyalists |        8827 |      1.19047e+06 |     8827 |
| Loyal Customers     |         874 | 231435           |     1830 |
| Champions           |          31 |  17675           |      115 |

## Category evidence

| category              |            sales |   units |   orders |
|:----------------------|-----------------:|--------:|---------:|
| health_beauty         |      1.23313e+06 |    9465 |     8647 |
| watches_gifts         |      1.16618e+06 |    5859 |     5495 |
| bed_bath_table        |      1.02343e+06 |   10953 |     9272 |
| sports_leisure        | 954853           |    8431 |     7530 |
| computers_accessories | 888725           |    7644 |     6530 |
| furniture_decor       | 711928           |    8160 |     6307 |
| housewares            | 615629           |    6795 |     5743 |
| cool_stuff            | 610204           |    3718 |     3559 |
| auto                  | 578967           |    4140 |     3810 |
| toys                  | 471286           |    4030 |     3804 |

## Comparable historical performance

July 2018 merchandise value was R$ 867,953.46, versus R$ 856,077.86 in June: +1.39%. Both months fall within the conservative modeling window. This comparison does not establish seasonality or a causal growth driver.

## Application evidence

![Executive dashboard](dashboard-overview.png)
