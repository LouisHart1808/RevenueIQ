"""Validate every raw row, preserve source records, load PostgreSQL atomically."""

from pathlib import Path
import json
import os
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from app.releases import identifier

ROOT = Path(__file__).resolve().parents[1]
URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://localhost:55432/revenueiq")
TABLES = {
    "customers": ["customer_id"],
    "orders": ["order_id"],
    "order_items": ["order_id", "order_item_id"],
    "order_payments": ["order_id", "payment_sequential"],
    "order_reviews": [],
    "products": ["product_id"],
    "sellers": ["seller_id"],
    "geolocation": [],
    "category_translation": ["product_category_name"],
}


def read_raw():
    result = {}
    for name in TABLES:
        filename = (
            "product_category_name_translation.csv" if name == "category_translation" else f"olist_{name}_dataset.csv"
        )
        result[name] = pd.read_csv(
            ROOT / "data/raw" / filename,
            dtype={
                c: str for c in ["geolocation_zip_code_prefix", "customer_zip_code_prefix", "seller_zip_code_prefix"]
            },
        )
    return result


def validate(frames):
    report = {"tables": {}, "errors": [], "warnings": []}
    for name, df in frames.items():
        keys = TABLES[name]
        report["tables"][name] = {
            "rows": len(df),
            "nulls": df.isna().sum().to_dict(),
            "exact_duplicates": int(df.duplicated().sum()),
            "columns": list(df),
        }
        if keys and (df.duplicated(keys).any() or df[keys].isna().any().any()):
            report["errors"].append(f"{name}: invalid primary key")
        for col in df:
            if col.endswith(("_timestamp", "_date", "_at")) or col in [
                "shipping_limit_date",
                "review_creation_date",
                "review_answer_timestamp",
            ]:
                bad = df[col].notna() & pd.to_datetime(df[col], errors="coerce").isna()
                if bad.any():
                    report["errors"].append(f"{name}.{col}: {bad.sum()} invalid dates")
            if col in ["price", "freight_value", "payment_value"] and (df[col] < 0).any():
                report["errors"].append(f"{name}.{col}: negative amounts")
    required = {
        "orders": ["order_id", "customer_id", "order_status", "order_purchase_timestamp"],
        "order_items": ["order_id", "order_item_id", "price", "freight_value", "product_id", "seller_id"],
        "order_payments": ["order_id", "payment_sequential", "payment_value"],
        "customers": ["customer_id", "customer_unique_id"],
        "order_reviews": ["order_id", "review_score"],
    }
    for name, columns in required.items():
        for column in columns:
            if column not in frames[name] or frames[name][column].isna().any():
                report["errors"].append(f"{name}.{column}: missing required values")
    relations = [
        ("orders", "customer_id", "customers", "customer_id"),
        ("order_items", "product_id", "products", "product_id"),
        ("order_items", "seller_id", "sellers", "seller_id"),
    ] + [(t, "order_id", "orders", "order_id") for t in ["order_items", "order_payments", "order_reviews"]]
    for child, key, parent, pkey in relations:
        missing = ~frames[child][key].isin(frames[parent][pkey])
        if missing.any():
            report["errors"].append(f"{child}.{key}: {missing.sum()} missing references")
    allowed = {"created", "approved", "invoiced", "processing", "shipped", "delivered", "unavailable", "canceled"}
    if not set(frames["orders"].order_status) <= allowed:
        report["errors"].append("Unexpected order status")
    report["warnings"] = [
        "Geolocation contains repeated ZIP codes: aggregate before joining.",
        "Review IDs are not assumed unique; preserve raw reviews and average per order.",
        "Missing attributes are retained; category labels use Unknown.",
        "Payment and item totals may differ; reconcile separately, never equate to profit.",
    ]
    orders = frames["orders"]
    purchased = pd.to_datetime(orders.order_purchase_timestamp)
    delivered = pd.to_datetime(orders.order_delivered_customer_date)
    report["coverage"] = {"first_purchase": str(purchased.min()), "last_purchase": str(purchased.max())}
    report["issues"] = {
        "delivery_before_purchase": int((delivered < purchased).sum()),
        "delivered_missing_delivery_date": int(((orders.order_status == "delivered") & delivered.isna()).sum()),
        "orders_missing_payment": int((~orders.order_id.isin(frames["order_payments"].order_id)).sum()),
        "orders_missing_items": int((~orders.order_id.isin(frames["order_items"].order_id)).sum()),
        "repeated_review_ids": int(frames["order_reviews"].duplicated("review_id").sum()),
    }
    for issue, count in report["issues"].items():
        if count:
            report["warnings"].append(f"{issue}: {count} records; preserved for audit.")
    (Path(os.getenv("REPORT_DIR", str(ROOT / "reports"))) / "data_quality.json").write_text(
        json.dumps(report, indent=2, default=int)
    )
    if report["errors"]:
        raise ValueError(report["errors"])
    return report


def main():
    frames = read_raw()
    report = validate(frames)
    engine = create_engine(URL)
    schema = identifier(os.getenv("RAW_SCHEMA", "raw"))
    with engine.begin() as conn:
        conn.execute(text(f"create schema if not exists {schema}"))
        for name, df in frames.items():
            if inspect(conn).has_table(name, schema=schema):
                conn.execute(text(f'TRUNCATE TABLE {schema}."{name}"'))
            df.to_sql(name, conn, schema=schema, if_exists="append", index=False, chunksize=5000, method="multi")
    print({name: d["rows"] for name, d in report["tables"].items()})


if __name__ == "__main__":
    main()
