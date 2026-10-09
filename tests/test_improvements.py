"""Failure, leakage, and evaluation tests use synthetic fixtures, never dashboard data."""

import json
import numpy as np
import pandas as pd
import pytest
from analytics.core import forecast
from analytics.validation import validate_baskets, clustered_review_difference
from pipelines.publication import publish


def test_forecast_selection_and_intervals_ignore_final_outcomes():
    original = np.array(
        [100, 110, 108, 123, 120, 132, 136, 139, 134, 148, 140, 157, 151, 159, 163, 170, 172, 166, 169.0]
    )
    altered = original.copy()
    altered[-3:] = [1000, 5, 900]
    a, b = forecast(original), forecast(altered)
    assert a["selected"] == b["selected"]
    assert a["scores"] == b["scores"]
    assert a["interval_width_frozen"] == b["interval_width_frozen"]
    assert a["predicted"][0] == b["predicted"][0]
    assert a["holdout_scores"] != b["holdout_scores"]
    assert len(a["actual"]) == 3 and a["folds"] == 4
    assert a["holdout_coverage"] == np.mean(
        (np.array(a["actual"]) >= a["lower"]) & (np.array(a["actual"]) <= a["upper"])
    )


def test_future_only_basket_pair_is_not_selected():
    rows = []
    for prefix, date, products in [("train", "2017-01-01", ["a", "b"]), ("test", "2018-02-01", ["x", "y"])]:
        for i in range(25):
            for product in products:
                rows.append({"order_id": f"{prefix}{i}", "product_id": product, "purchase_date": date})
    result = validate_baskets(pd.DataFrame(rows))
    assert result["candidate_pairs"] == 1
    assert all(r["antecedent"] in ["a", "b"] for r in result["rules"])
    assert all(r["test_orders"] == 0 and not r["replicated"] for r in result["rules"])


def test_two_way_cluster_interval_and_row_order():
    rng = np.random.default_rng(33)
    n = 1200
    sellers = np.arange(n) % 40
    customers = np.arange(n) // 2
    late = rng.binomial(1, 0.25, n)
    frame = pd.DataFrame(
        {
            "order_id": np.arange(n).astype(str),
            "customer_unique_id": customers,
            "seller_id": sellers,
            "on_time": late == 0,
            "review_score": 4 - 0.8 * late + rng.normal(0, 0.3, 40)[sellers] + rng.normal(0, 0.1, n),
        }
    )
    result = clustered_review_difference(frame)
    assert result["supported"] and result["ci95"][1] < 0
    assert result == clustered_review_difference(frame.iloc[::-1])


def test_failed_validation_cannot_publish(tmp_path):
    for name in ["analytics.json", "executive_report.md", "refresh_log.json"]:
        (tmp_path / name).write_text("{}")
    (tmp_path / "data_quality.json").write_text(json.dumps({"errors": ["broken"]}))
    with pytest.raises(ValueError, match="quality"):
        publish(None, "release_test", tmp_path)


def test_failed_dbt_cannot_publish(tmp_path):
    for name in ["analytics.json", "executive_report.md", "refresh_log.json"]:
        (tmp_path / name).write_text("{}")
    (tmp_path / "data_quality.json").write_text(json.dumps({"errors": []}))
    (tmp_path / "dbt_run_results.json").write_text(json.dumps({"results": [{"status": "fail"}]}))
    with pytest.raises(ValueError, match="dbt"):
        publish(None, "release_test", tmp_path)


def test_product_search_is_literal_and_sort_is_allowlisted():
    from app.services import product_query, product_order

    sql, params = product_query(search="x%_' OR 1=1 --")
    assert "OR 1=1" not in sql
    assert params["product_search"] == "%x!%!_' OR 1=1 --%"
    assert product_order("sales; drop table orders") == " order by sales desc, product_id asc"
    assert product_order("category") == " order by category asc, product_id asc"


def test_zero_value_scenario_has_explanatory_empty_state():
    from app.main import simulate

    assert "positive merchandise-value baseline" in str(simulate(1, 1, 1, 0))
