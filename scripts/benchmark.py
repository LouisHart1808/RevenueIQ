import json
import time
from pathlib import Path
from app.services import snapshot, get_snapshot
from app.main import render

measurements = []
for args in [
    (None, None, None, None),
    ("2018-01-01", "2018-06-30", "SP", None),
    ("2017-01-01", "2018-07-31", None, "health_beauty"),
]:
    snapshot.cache_clear()
    row = {"filters": args}
    for name in ["cold_seconds", "cached_seconds"]:
        start = time.perf_counter()
        get_snapshot(*args)
        row[name] = time.perf_counter() - start
    measurements.append(row)
start = time.perf_counter()
render(0, "2016-09-04", "2018-10-17", None, None)
Path("reports/performance.json").write_text(
    json.dumps(
        {
            "query_snapshots": measurements,
            "overview_callback_seconds": time.perf_counter() - start,
            "scope": "Local PostgreSQL; includes query conversion, excludes browser paint. Release-keyed process-local cache; cached calls include the live publication lookup.",
        },
        indent=2,
    )
)
