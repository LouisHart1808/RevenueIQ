# RevenueIQ delivery: reliability and analytical validation revision

## Delivered capabilities
The platform contains nine working Dash pages, reproducible Olist acquisition, PostgreSQL/dbt models, semantic definitions, actual analytical findings and an executive report. This revision implements the six requested improvements:

1. Customer features stop at the selected cutoff and exclude unknown/future deliveries. Cohort membership is defined at acquisition, then followed only through the cutoff.
2. Forecast model selection and interval calibration use development months only. May–July 2018 provide a locked retrospective test, with measured interval coverage and a fixed last-month reference.
3. Warehouse schemas and reports are versioned. Atomic publication changes one active version, requests remain pinned, and cache keys switch immediately on subsequent requests. Failed promotion and rollback are tested.
4. Category, region and seller chart clicks drive shared filters. Currency/percentage labels and drill-down feedback are clearer.
5. Delivery-review evidence includes customer/seller-clustered uncertainty. Basket candidates are selected before 2018 and evaluated later with a declared replication rule and multiple-testing correction.
6. The README, methodology, architecture, portfolio summary and walkthrough are updated for publication.

## Data and findings
Olist provides 99,441 source orders and 112,650 items under CC BY-NC-SA 4.0. Raw files, databases, private release folders and user-supplied project instructions are excluded from Git. Original software is MIT; applicable dataset derivatives retain their separate obligations.

The retrospective delivered population remains 96,478 orders, 93,358 customers, R$13,221,498.11 merchandise value, R$137.04 AOV, 3.00% repeat purchasing and 93.23% on-time delivery among eligible dated orders. These are not profit or recognized accounting revenue.

The stronger methods reveal limitations: the selected forecast has approximately 14.79% WAPE on the three final months and its empirical band covers one of three outcomes. No product pair passes the declared later-period replication rule. On 94,563 single-seller reviewed orders, the customer/seller-clustered mean review difference is −2.038 points, with approximate 95% interval [−2.086, −1.990]. Association remains noncausal.

## Evidence and operation
Published at [LouisHart1808/RevenueIQ](https://github.com/LouisHart1808/RevenueIQ). The [initial hosted run](https://github.com/LouisHart1808/RevenueIQ/actions/runs/37909490186) passed lint, unit tests, real-data refresh/publication, database tests, browser acceptance and Docker build. Its cleanup exposed a background-server cache lock; the workflow now stops that server on exit. Final revision status is available from the README badge.

Local acceptance: 29 database-enabled tests passed; all nine browser views, category/state/seller chart clicks, filter resets, CSV export, cohort selection, scenario controls and 390-pixel mobile layout passed with no JavaScript errors. The recorded demo is in [walkthrough.webm](../reports/walkthrough.webm).

See `reports/analytics.json`, `reports/data_quality.json`, `reports/browser_validation.json`, `reports/performance.json` and the hosted CI workflow for current evidence. Regression tests include future-purchase exclusion, future-delivery exclusion, selection/calibration leakage, candidate leakage, clustered inference, mid-request promotion, immediate cache-version changes and failed-publication rollback in a disposable database.

The local application runs at http://127.0.0.1:8050 . Use `docker compose run --rm app python scripts/refresh.py` for an atomic refresh. Use `docker compose run --rm -e RUN_INTEGRATION=1 app pytest -q` for database-enabled tests. Full setup and rollback instructions are in the README.

## Limits
The previously explored historical dataset cannot provide genuinely never-viewed external validation. Three test months cannot establish forecast reliability. Cluster corrections do not remove confounding or review nonresponse, and association tests still face dependence and nonstationarity. The dataset has no costs, marketing ledger or status-event history.

The application remains a local portfolio deployment without authentication or internet-facing hardening. Retention of old releases is manual. These limits are documented rather than represented as completed production capabilities or measured business uplift.

## Maintainability and explorer enhancement
Shared presentation helpers and basket predicates are extracted into focused modules. Product charts, pagination, counts and exports use a common aggregation. The explorer adds literal category/product-ID search, allowlisted sorting, total counts and page bounds; exports include every matching product. Category charts now support the advertised drill-down, and zero-value scenarios display an explanatory state. Regression coverage includes search escaping, sort safety, complete exports and browser-driven search/sort/download checks.
