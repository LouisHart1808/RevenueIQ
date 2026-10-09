import os
import pytest

pytestmark = pytest.mark.skipif(os.getenv("RUN_INTEGRATION") != "1", reason="Requires loaded PostgreSQL warehouse")
from app.services import get_snapshot, query  # noqa: E402


def test_filtered_reconciliation():
    for filters in [
        (None, None, None, None),
        ("2018-01-01", "2018-06-30", "SP", None),
        ("2017-01-01", "2018-07-31", None, "health_beauty"),
    ]:
        s = get_snapshot(*filters)
        assert s["kpi"].iloc[0].sales == pytest.approx(s["categories"].sales.sum(), abs=0.01)
        assert s["kpi"].iloc[0].orders == s["monthly"].orders.sum()


def test_cohort_censoring():
    df = query("select cohort, max(age) as max_age from warehouse.mart_cohort group by cohort order by cohort")
    assert df.iloc[-1].max_age == 0
    assert len(df) > 12


def test_pages_and_empty_state():
    from app.main import app, render, simulate, cohort

    client = app.server.test_client()
    assert client.get("/").status_code == 200
    assert client.get("/_dash-layout").status_code == 200
    for page in range(9):
        title, content = render(page, "2016-09-04", "2018-10-17", None, None)
        assert "could not load" not in str(content)
        assert title
    assert "No delivered orders" in str(render(0, "2020-01-01", "2020-02-01", None, None))
    assert "on or after" in str(render(0, "2018-01-01", "2017-01-01", None, None))
    assert simulate(5, 3, 2, 100)
    assert len(cohort("2017-01-01").data) == 2


def test_server_pagination_and_seller_filter():
    from app.services import product_page

    first = product_page(0, 20)
    second = product_page(1, 20)
    assert len(first) == len(second) == 20
    assert not set(first.product_id) & set(second.product_id)
    seller = query("select seller_id from warehouse.dim_sellers limit 1").iloc[0].seller_id
    s = get_snapshot(None, None, None, None, seller)
    assert s["kpi"].iloc[0].sales == pytest.approx(s["categories"].sales.sum(), abs=0.01)
