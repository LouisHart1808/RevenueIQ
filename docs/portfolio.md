# Portfolio summary

RevenueIQ is a local e-commerce intelligence application that transforms Olist's historical marketplace records into a tested PostgreSQL warehouse, nine interactive Dash views, and an evidence-based executive report.

## Resume bullets
- Built a reproducible Python/PostgreSQL/dbt analytical pipeline for 99,441 source orders and 112,650 order items, preserving persistent customer identity and preventing fact-join multiplication.
- Developed nine Plotly Dash views covering sales decomposition, RFM, cohort retention, products, delivery, geography, forecasting and assumption-based scenarios, with shared filters and CSV exports.
- Implemented release-pinned atomic warehouse publication and rollback, date-aware customer analytics, development/holdout forecast separation, and customer/seller-clustered uncertainty checks.

## Technical skills
Python, PostgreSQL, SQL, dbt Core, pandas, NumPy, SciPy, statsmodels, Plotly Dash, dimensional modeling, pytest, Playwright, Docker Compose, Ruff, GitHub Actions configuration.

## Business impact
Demonstrates a repeatable path from raw marketplace records to reconciled metrics and testable recommendations. No actual revenue uplift, cost reduction, retention improvement, or operational intervention is claimed.

## Technical interview questions
1. Why does joining order items, payments and reviews inflate sales, and how did the model avoid it?
2. How does customer_unique_id differ from customer_id?
3. How are unobserved future cohort ages different from zero retention?
4. Why can a development-selected forecasting method underperform a simple baseline on the locked test period?
5. How do immutable schemas, transactionally published metadata, request pinning, and release-keyed caches prevent mixed-version dashboards?

## Business analytics interview questions
1. Why is merchandise value not equivalent to recognized revenue or profit?
2. What evidence would justify acting on the delivery-rating relationship?
3. How would you test a retention intervention when historical repeat rates are low?
4. Which missing financial data prevents category profit prioritization?
5. How would you communicate an assumption-based 3% frequency opportunity to leadership?
