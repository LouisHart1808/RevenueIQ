"""Test-only synthetic inputs, never used as business evidence."""

import pytest
import pandas as pd
from analytics.core import revenue_anomalies
from app.services import predicate


def test_filter_values_are_bound():
    where, params = predicate("2018-01-01", "2018-02-01", "SP' OR 1=1 --", "health_beauty")
    assert "SP'" not in where
    assert params["state"] == "SP' OR 1=1 --"
    assert "exists" in where


def test_anomaly_constant_growth():
    df = pd.DataFrame({"sales": [100, 110, 121, 133.1]})
    assert not revenue_anomalies(df).flag.any()


def test_decomposition_invalid():
    from analytics.core import decompose

    with pytest.raises(ValueError):
        decompose([1, 2], [1, 2, 3])


@pytest.fixture
def raw_fixture(tmp_path, monkeypatch):
    """Tiny synthetic records only for failure-path tests; never dashboard data."""
    import pipelines.ingest as ingestion

    monkeypatch.setattr(ingestion, "ROOT", tmp_path)
    (tmp_path / "reports").mkdir()
    return {
        "orders": pd.DataFrame(
            [
                {
                    "order_id": "o1",
                    "customer_id": "c1",
                    "order_status": "delivered",
                    "order_purchase_timestamp": "2018-01-01",
                    "order_delivered_customer_date": "2018-01-03",
                }
            ]
        ),
        "customers": pd.DataFrame([{"customer_id": "c1", "customer_unique_id": "u1"}]),
        "order_items": pd.DataFrame(
            [
                {
                    "order_id": "o1",
                    "order_item_id": 1,
                    "product_id": "p1",
                    "seller_id": "s1",
                    "price": 10.0,
                    "freight_value": 1.0,
                }
            ]
        ),
        "order_payments": pd.DataFrame([{"order_id": "o1", "payment_sequential": 1, "payment_value": 11.0}]),
        "order_reviews": pd.DataFrame([{"order_id": "o1", "review_id": "r1", "review_score": 4}]),
        "products": pd.DataFrame([{"product_id": "p1"}]),
        "sellers": pd.DataFrame([{"seller_id": "s1"}]),
        "geolocation": pd.DataFrame([{"geolocation_state": "SP"}]),
        "category_translation": pd.DataFrame([{"product_category_name": "test_only"}]),
    }


def test_raw_negative_amount_is_rejected(raw_fixture):
    from pipelines.ingest import validate

    raw_fixture["order_items"].loc[0, "price"] = -1
    with pytest.raises(ValueError, match="negative amounts"):
        validate(raw_fixture)


def test_raw_duplicate_order_is_rejected(raw_fixture):
    from pipelines.ingest import validate

    raw_fixture["orders"] = pd.concat([raw_fixture["orders"]] * 2, ignore_index=True)
    with pytest.raises(ValueError, match="invalid primary key"):
        validate(raw_fixture)


def test_raw_missing_reference_is_rejected(raw_fixture):
    from pipelines.ingest import validate

    raw_fixture["order_items"].loc[0, "seller_id"] = "missing"
    with pytest.raises(ValueError, match="missing references"):
        validate(raw_fixture)
