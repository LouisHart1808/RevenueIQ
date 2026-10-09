"""Atomic publication: pointer, SQL facade, and immutable report directory agree."""

import json
from pathlib import Path
from sqlalchemy import text
from app.releases import identifier


def publish(engine, schema, reports):
    schema = identifier(schema)
    reports = Path(reports)
    for name in ["analytics.json", "data_quality.json", "executive_report.md", "refresh_log.json"]:
        if not (reports / name).is_file():
            raise ValueError(f"Missing release artifact: {name}")
    if json.loads((reports / "data_quality.json").read_text())["errors"]:
        raise ValueError("Cannot publish failing quality checks")
    validation = json.loads((reports / "dbt_run_results.json").read_text())["results"]
    if not validation or any(r["status"] not in ["success", "pass"] for r in validation):
        raise ValueError("Cannot publish a failed or skipped dbt build")
    with engine.begin() as conn:
        models = (
            conn.execute(
                text("select table_name from information_schema.tables where table_schema=:schema order by table_name"),
                {"schema": schema},
            )
            .scalars()
            .all()
        )
        expected = {
            result["unique_id"].rsplit(".", 1)[-1] for result in validation if result["unique_id"].startswith("model.")
        }
        if set(models) != expected:
            raise ValueError("Built schema does not match the validated model set")
        if "fact_orders" not in models or "mart_cohort" not in models:
            raise ValueError("Warehouse is incomplete")
        conn.execute(text("create schema if not exists revenueiq_meta"))
        conn.execute(
            text(
                "create table if not exists revenueiq_meta.publication(singleton boolean primary key default true check(singleton),schema_name text not null,published_at timestamptz not null default now())"
            )
        )
        conn.execute(
            text(
                "create table if not exists revenueiq_meta.history(schema_name text primary key,published_at timestamptz not null default now())"
            )
        )
        # One-time migration preserves the original local tables for recovery.
        physical = conn.scalar(
            text(
                "select count(*) from information_schema.tables where table_schema='warehouse' and table_type='BASE TABLE'"
            )
        )
        if physical:
            legacy = identifier("legacy_" + schema.removeprefix("release_"))
            conn.execute(text(f"alter schema warehouse rename to {legacy}"))
        conn.execute(text("create schema if not exists warehouse"))
        for model in models:
            name = identifier(model)
            conn.execute(text(f"create or replace view warehouse.{name} as select * from {schema}.{name}"))
        conn.execute(
            text("insert into revenueiq_meta.history(schema_name) values(:schema) on conflict do nothing"),
            {"schema": schema},
        )
        conn.execute(
            text(
                "insert into revenueiq_meta.publication(singleton,schema_name) values(true,:schema) on conflict(singleton) do update set schema_name=excluded.schema_name,published_at=now()"
            ),
            {"schema": schema},
        )
