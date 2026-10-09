"""Pin one immutable warehouse/report release for each request and cache key."""

from contextvars import ContextVar
from functools import wraps
from pathlib import Path
import os
import re
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
PINNED = ContextVar("revenueiq_release", default=None)


def identifier(value):
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", value):
        raise ValueError("Invalid database identifier")
    return value


def current_release(engine):
    override = os.getenv("WAREHOUSE_SCHEMA")
    if override:
        return identifier(override)
    pinned = PINNED.get()
    if pinned:
        return pinned
    with engine.connect() as conn:
        exists = conn.scalar(text("select to_regclass('revenueiq_meta.publication')"))
        if exists:
            return (
                conn.scalar(text("select schema_name from revenueiq_meta.publication where singleton=true"))
                or "warehouse"
            )
    return "warehouse"


def pinned_release(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        from app.services import ENGINE

        token = PINNED.set(current_release(ENGINE))
        try:
            return func(*args, **kwargs)
        finally:
            PINNED.reset(token)

    return wrapped


def report_path(name):
    from app.services import ENGINE

    release = current_release(ENGINE)
    override = os.getenv("REPORT_DIR")
    folder = (
        Path(override)
        if override
        else ROOT / "reports"
        if release == "warehouse"
        else ROOT / "reports/releases" / release
    )
    return folder / name
