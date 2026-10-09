# Stronger analytical validation

## Forecast protocol
Use January 2017–July 2018 monthly delivered merchandise value. Exclude launch and terminal extraction periods. The first 12 months initialize candidate methods. January–April 2018 are expanding one-month-ahead development folds used to select the lowest-MAE method and freeze an empirical 95th-percentile absolute-error width. May–July 2018 are excluded from both decisions.

The selected method is refitted before each test month using only observations then available. Previously observed test outcomes may enter later one-step training; they never change the selected algorithm or interval width. Report final MAE/RMSE/WAPE/sMAPE and interval coverage, alongside the fixed last-month reference. Do not switch the winner after reading holdout outcomes.

The earlier project version explored this dataset, including these months. This is a retrospective locked evaluation, not genuinely never-viewed external data. Four calibration errors and three test outcomes are inadequate to establish nominal 95% coverage. Low measured coverage is displayed, not suppressed.

Reference: [Forecasting: Principles and Practice — evaluating accuracy](https://otexts.com/fpp3/accuracy.html).

## Delivery and reviews
Retain the original all-reviewed-order mean comparison and seeded order bootstrap as a descriptive baseline. Add a sensitivity analysis restricted to single-seller reviewed orders. Fit review score on an intercept and late-delivery indicator; estimate covariance clustered jointly by persistent customer and seller with finite-sample correction. Report the coefficient, cluster counts and normal-approximation 95% interval.

This handles dependence within these observed groups, but not arbitrary dependence between groups, missing-review selection or confounding. Excluding multi-seller orders changes the population and is clearly reported. No causal intervention effect is claimed.

Reference: [statsmodels two-group clustered covariance](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_cluster_2groups.html).

## Product associations
Select unique unordered product pairs with at least 20 co-purchases before 1 January 2018. Freeze this candidate set, then evaluate every candidate on 2018 baskets. Compute support, confidence and lift in each period; a one-sided Fisher test evaluates positive association in the later period. Apply Benjamini–Hochberg correction across unique candidate pairs before expanding directional rules.

The declared replication rule requires at least five later co-purchases, lift >1 and q≤0.05. This count rule is a basic evidence floor, not a power analysis. Overlapping baskets/products, repeat customers and changing availability can violate assumptions. A candidate failing the rule is not recommended even if its lift looks large. No threshold is tuned after observing validation outcomes.
