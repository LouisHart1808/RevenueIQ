from pathlib import Path
import json
import os
import pandas as pd
from app.services import query, get_snapshot
from analytics.core import compare_reviews, forecast
from analytics.validation import clustered_review_difference, validate_baskets
from app.releases import pinned_release

ROOT = Path(__file__).resolve().parents[1]


@pinned_release
def main():
    output = Path(os.getenv("REPORT_DIR", str(ROOT / "reports")))
    output.mkdir(parents=True, exist_ok=True)
    reviews = query(
        "select review_score,on_time from warehouse.fact_orders where order_status='delivered' and review_score is not null and on_time is not null"
    )
    stats = compare_reviews(reviews.loc[~reviews.on_time, "review_score"], reviews.loc[reviews.on_time, "review_score"])
    monthly = query("select * from warehouse.mart_revenue order by month")
    # Exclude first/last purchase months and sparse 2016 launch period; freeze before terminal extraction tail.
    complete = monthly[(pd.to_datetime(monthly.month) >= "2017-01-01") & (pd.to_datetime(monthly.month) < "2018-08-01")]
    fc = forecast(complete.sales)
    items = query(
        "select i.order_id,i.product_id,o.purchase_date from warehouse.fact_order_items i join warehouse.fact_orders o using(order_id) where o.order_status='delivered'"
    )
    basket = validate_baskets(items)
    clustered = query(
        "with single_seller as (select order_id,min(seller_id) as seller_id from warehouse.fact_order_items group by 1 having count(distinct seller_id)=1) select o.order_id,o.customer_unique_id,s.seller_id,o.review_score,o.on_time from warehouse.fact_orders o join single_seller s using(order_id) where o.order_status='delivered' and o.review_score is not null and o.on_time is not null"
    )
    stats["clustered"] = clustered_review_difference(clustered)
    fc["development_months"] = complete.month.astype(str).tolist()[12 : fc["holdout_start_index"]]
    fc["test_months"] = complete.month.astype(str).tolist()[fc["holdout_start_index"] :]
    result = {
        "statistics": stats,
        "forecast": fc,
        "basket": basket,
        "forecast_months": complete.month.astype(str).tolist(),
    }
    (output / "analytics.json").write_text(json.dumps(result, indent=2))
    snap = get_snapshot()
    for name, df in snap.items():
        df.to_csv(output / f"{name}.csv", index=False)
    k = snap["kpi"].iloc[0]
    top = snap["categories"].iloc[0]
    region = snap["regions"].iloc[0]
    repeat = snap["repeat"].iloc[0].rate
    report = f"""# RevenueIQ — Executive business report

Historical Olist marketplace sample • BRL • delivered-order merchandise value • generated from PostgreSQL.

## Executive summary
The observed delivered population contains {int(k.orders):,} orders from {int(k.customers):,} persistent purchasing customers. Merchandise sales total R$ {k.sales:,.2f}; average order value is R$ {k.aov:,.2f}. This is transaction value, not Olist revenue, net revenue, or profit. Repeat purchase rate across the observed window is {repeat:.2%}. On-time delivery is {k.on_time:.2%} among eligible delivered orders with actual and estimated dates.

## Commercial performance
The largest category is {top.category}, with R$ {top.sales:,.2f} ({top.sales / k.sales:.2%} of merchandise value). The largest state is {region.state}, with R$ {region.sales:,.2f} ({region.sales / k.sales:.2%}). See [monthly results](monthly.csv), [category results](categories.csv), and [regional results](regions.csv). Growth is descriptive; the launch period and terminal extraction tail cannot support clean annual seasonality claims.

## Customers
Repeat purchasing is sparse ({repeat:.2%}), making predictive customer lifetime value unreliable without additional history. Use observed monetary value and rule-based RFM as descriptions of this sample. The application rebuilds customer labels from known deliveries by the selected date; no later purchases or deliveries enter those features. These report tables use the full available cutoff, never today's customer status. Cohort ages beyond the observable window are absent, not zero. Recommendations should be tested against newer, longer customer histories.

## Delivery and satisfaction
Late reviewed orders: {stats.get("late_n", 0):,}; on-time reviewed orders: {stats.get("on_time_n", 0):,}. Mean review difference (late minus on-time): {stats.get("mean_difference", 0):.3f} points; bootstrap 95% interval [{stats["ci95"][0]:.3f}, {stats["ci95"][1]:.3f}]. Two-sided Mann–Whitney p={stats.get("p_value_note") if stats.get("p_value") == 0 else stats.get("p_value")}; rank-biserial effect {stats.get("rank_biserial", 0):.3f}. The null is equal score distributions; the alternative is a distributional difference. Reviews are averaged within order. Bootstrap resamples orders with seed 42, assuming independent orders; seller/customer clustering and nonresponse may bias uncertainty. This observational association cannot establish that delivery improvements cause better ratings or more sales.

## Forecasting
This retrospective exercise uses January 2017–July 2018, excludes the sparse launch period and terminal tail, and compares last-month, three-month mean, seasonal-naive, and damped-trend forecasts with expanding chronological backtests. Selected model: {fc.get("selected")}; development folds: {fc.get("folds")}. May–July 2018 are withheld from model selection and interval calibration. The fixed method is evaluated with expanding one-step forecasts; prior test observations become available only for later forecasts. Holdout MAE: R$ {fc["holdout_scores"]["MAE"]:,.2f}; WAPE: {fc["holdout_scores"]["WAPE"]:.2%}; empirical interval coverage: {fc["holdout_coverage"]:.1%} across {fc["holdout_months"]} test months. Metrics are in [analytics.json](analytics.json). This dataset was explored in v1, so this is retrospective locked evaluation, not never-viewed external data. The 95% band uses frozen development errors; the small sample cannot establish nominal coverage. No present-day sales forecast is claimed.

## Prioritized recommendations
|Priority / finding|Evidence|Action and implication|Assumption-based impact|Confidence and validation|
|---|---|---|---|---|
|1. Investigate late deliveries|Review-score difference and interval above|Audit high-volume sellers and shipping lanes before intervention|No causal sales estimate supported|Moderate association evidence; run a randomized or phased operational trial, tracking ratings and lateness|
|2. Validate retention opportunity|Observed repeat rate {repeat:.2%}|Collect longer customer histories, then test relevant replenishment reminders|A hypothetical 3% frequency uplift at constant customers and AOV implies R$ {k.sales * 0.03:,.2f} additional merchandise value|Low confidence in uplift assumption; use a holdout experiment and measure incremental orders|
|3. Examine leading category concentration|{top.category} contributes {top.sales / k.sales:.2%}|Review capacity, assortment, and seller reliability in this category|No profit impact can be sized without cost data|High confidence in historical share; validate demand and margins with current records|

## Product affinity
{result["basket"]["multi_product_orders"]:,} of {result["basket"]["total_orders"]:,} delivered baskets contain distinct products. Candidates require at least 20 co-purchases before January 2018. All candidates are evaluated on subsequent baskets, with BH multiple-testing correction across unique pairs. Replication requires at least 5 test co-purchases, lift above 1 and q ≤0.05; {basket["replicated_pairs"]} of {basket["candidate_pairs"]} candidates meet that rule. Dependence and changing assortment remain limitations; do not launch campaigns on this evidence alone.

## Limitations
Historical anonymized sample, unknown marketplace sampling completeness, sparse repeats, no cost/marketing/refund ledger, and possible review-selection bias. Paid totals, shipping, and merchandise differ legitimately. Actual delivery timestamps determine punctuality at calendar-day precision. Geographic displays use aggregate state coordinates and do not reveal customer addresses. Customer features stop at the selected cutoff and include only orders known delivered by it. Unknown delivery dates are excluded from those features. Other revenue views remain retrospective final-status merchandise measures. Source attribution: Olist, Brazilian E-Commerce Public Dataset, Kaggle, CC BY-NC-SA 4.0. Analytical outputs inherit applicable source-license obligations; code is separately licensed.
"""
    cluster = stats["clustered"]
    if cluster["supported"]:
        report += f"\n## Dependence-aware delivery evidence\n\nOn {cluster['orders']:,} single-seller reviewed orders, the mean difference is {cluster['mean_difference']:.3f} points; two-way customer/seller clustered 95% interval [{cluster['ci95'][0]:.3f}, {cluster['ci95'][1]:.3f}]. This uses {cluster['customer_clusters']:,} customer clusters and {cluster['seller_clusters']:,} seller clusters, finite-sample covariance correction and a normal critical value. Multi-seller orders are excluded from this sensitivity analysis to avoid assigning a shared outcome to one arbitrary seller. Confounding and review nonresponse remain.\n"
    report += (
        "\n## Locked forecast test metrics\n\n"
        + pd.DataFrame([fc["holdout_scores"]]).round(4).to_markdown(index=False)
        + "\n"
    )
    forecast_table = pd.DataFrame(fc["scores"]).T.rename_axis("Model").reset_index()
    report += "\n## Development-only model comparison\n\n" + forecast_table.round(4).to_markdown(index=False) + "\n"
    report += "\n## Customer segment evidence\n\n" + snap["segments"].round(2).to_markdown(index=False) + "\n"
    report += "\n## Category evidence\n\n" + snap["categories"].head(10).round(2).to_markdown(index=False) + "\n"
    if len(complete) >= 2:
        prior, current = complete.iloc[-2], complete.iloc[-1]
        report += f"\n## Comparable historical performance\n\nJuly 2018 merchandise value was R$ {current.sales:,.2f}, versus R$ {prior.sales:,.2f} in June: {current.sales / prior.sales - 1:+.2%}. Both months fall within the conservative modeling window. This comparison does not establish seasonality or a causal growth driver.\n"
    report += "\n## Application evidence\n\n![Executive dashboard](dashboard-overview.png)\n"
    (output / "executive_report.md").write_text(report)
    print(json.dumps({"orders": int(k.orders), "sales": float(k.sales), "statistics": stats, "forecast": fc}, indent=2))


if __name__ == "__main__":
    main()
