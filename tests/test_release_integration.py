"""Atomic promotion tests run only in a disposable database, never the application DB."""

from functools import lru_cache
import json
import os
import uuid
import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from app import services, releases
from pipelines.publication import publish
from app.customers import customer_cte

pytestmark = pytest.mark.skipif(os.getenv("RUN_INTEGRATION") != "1", reason="Requires local PostgreSQL")


def test_asof_features_ignore_future_purchase_and_delivery():
    schema = "test_asof_" + uuid.uuid4().hex[:10]
    with services.ENGINE.begin() as conn:
        conn.execute(text(f"create schema {schema}"))
        try:
            conn.execute(
                text(
                    f"create table {schema}.fact_orders(customer_unique_id text,purchase_date date,delivered_at timestamp,order_status text,sales numeric)"
                )
            )
            conn.execute(
                text(
                    f"insert into {schema}.fact_orders values ('c','2017-01-01','2017-01-02','delivered',100),('other','2017-12-31','2018-01-03','delivered',10)"
                )
            )
            sql = (
                customer_cte().replace("warehouse.", schema + ".")
                + "select * from customer_asof order by customer_unique_id"
            )
            before = pd.read_sql(text(sql), conn, params={"as_of": "2017-06-30"})
            conn.execute(
                text(
                    f"insert into {schema}.fact_orders values ('c','2017-07-01','2017-07-02','delivered',500),('c','2017-06-20','2017-07-05','delivered',800)"
                )
            )
            after = pd.read_sql(text(sql), conn, params={"as_of": "2017-06-30"})
            pd.testing.assert_frame_equal(before, after)
            assert before.iloc[0].frequency == 1 and before.iloc[0].monetary == 100
        finally:
            conn.execute(text(f"drop schema {schema} cascade"))


def test_atomic_publication_pins_requests_invalidates_cache_and_rolls_back(tmp_path, monkeypatch):
    database = "revenueiq_test_" + uuid.uuid4().hex[:10]
    admin = create_engine(services.ENGINE.url, isolation_level="AUTOCOMMIT")
    engine = None
    with admin.connect() as conn:
        conn.execute(text(f"create database {database}"))
    try:
        engine = create_engine(services.ENGINE.url.set(database=database))
        monkeypatch.setattr(services, "ENGINE", engine)
        monkeypatch.setattr(releases, "ROOT", tmp_path)

        def artifact(schema):
            folder = tmp_path / "reports/releases" / schema
            folder.mkdir(parents=True)
            for name in ["analytics.json", "refresh_log.json"]:
                (folder / name).write_text("{}")
            (folder / "executive_report.md").write_text("Test-only fixture")
            (folder / "data_quality.json").write_text(json.dumps({"errors": []}))
            (folder / "dbt_run_results.json").write_text(
                json.dumps(
                    {
                        "results": [
                            {"unique_id": f"model.test.{m}", "status": "success"}
                            for m in ["fact_orders", "mart_cohort"]
                        ]
                    }
                )
            )
            return folder

        with engine.begin() as conn:
            for schema, value, kind in [
                ("release_a", 1, "numeric"),
                ("release_b", 2, "numeric"),
                ("release_bad", 3, "text"),
            ]:
                conn.execute(text(f"create schema {schema}"))
                conn.execute(text(f"create table {schema}.fact_orders(value {kind})"))
                conn.execute(text(f"insert into {schema}.fact_orders values ('{value}')"))
                conn.execute(text(f"create table {schema}.mart_cohort(value numeric)"))
        folders = {s: artifact(s) for s in ["release_a", "release_b", "release_bad"]}
        publish(engine, "release_a", folders["release_a"])

        @lru_cache(maxsize=8)
        def cached(*args, release):
            return services.query("select value from warehouse.fact_orders").iloc[0, 0]

        monkeypatch.setattr(services, "snapshot", cached)
        assert services.get_snapshot() == 1

        @releases.pinned_release
        def request_during_promotion():
            before = services.query("select value from warehouse.fact_orders").iloc[0, 0]
            publish(engine, "release_b", folders["release_b"])
            after = services.query("select value from warehouse.fact_orders").iloc[0, 0]
            assert releases.report_path("analytics.json").parent == folders["release_a"]
            return before, after

        assert request_during_promotion() == (1, 1)
        assert services.get_snapshot() == 2  # No TTL wait or worker restart.
        assert cached.cache_info().misses == 2
        with pytest.raises(DBAPIError):
            publish(engine, "release_bad", folders["release_bad"])
        assert releases.current_release(engine) == "release_b"
        with engine.connect() as conn:
            assert conn.scalar(text("select value from warehouse.fact_orders")) == 2
        assert services.get_snapshot() == 2
    finally:
        if engine:
            engine.dispose()
        with admin.connect() as conn:
            conn.execute(text(f"drop database {database} with (force)"))
        admin.dispose()
