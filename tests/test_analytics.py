import numpy as np
import pytest
from analytics.core import scenario, decompose, errors, compare_reviews, forecast


def test_shapley_reconciles_and_symmetric():
    rng = np.random.default_rng(19)
    for _ in range(100):
        a = rng.uniform(1, 100, 3)
        b = rng.uniform(1, 100, 3)
        assert sum(decompose(a, b)) == pytest.approx(np.prod(b) - np.prod(a))
        np.testing.assert_allclose(decompose(b, a), -decompose(a, b))


def test_scenario_compounds():
    assert scenario(100, 0.1, 0.2, 0.3) == pytest.approx(171.6)
    assert scenario(100, -1) == 0


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1.1])
def test_scenario_rejects_invalid(value):
    with pytest.raises(ValueError):
        scenario(100, value)


def test_error_metrics():
    m = errors([100, 200], [90, 220])
    assert m["MAE"] == 15
    assert m["WAPE"] == 0.1
    assert errors([0], [0])["WAPE"] is None


def test_insufficient_evidence():
    assert not compare_reviews([1], [5])["supported"]
    assert not forecast([1, 2, 3])["supported"]


def test_forecast_constant_series():
    result = forecast(np.full(19, 100.0))
    assert result["folds"] == 4
    assert result["scores"]["Seasonal naive"]["MAE"] == 0
    assert result["next"] == pytest.approx(100)


def test_bootstrap_is_invariant_to_database_row_order():
    a = np.array([1, 2, 3, 4, 5] * 5)
    b = np.array([2, 3, 4, 5, 5] * 5)
    assert compare_reviews(a, b, iterations=50) == compare_reviews(a[::-1], b[::-1], iterations=50)
