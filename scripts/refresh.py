"""Build and validate in isolation; atomically publish only a complete release."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipelines.publication import publish  # noqa: E402
from app.releases import identifier  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    release = "release_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "_" + uuid.uuid4().hex[:8]
    reports = ROOT / "reports/releases" / release
    reports.mkdir(parents=True)
    env = os.environ.copy()
    env.update(WAREHOUSE_SCHEMA=release, RAW_SCHEMA="raw_" + release, REPORT_DIR=str(reports))
    engine = create_engine(os.getenv("DATABASE_URL", "postgresql+psycopg2://localhost:55432/revenueiq"))
    with engine.connect() as lock:
        if not lock.scalar(text("select pg_try_advisory_lock(71401926)")):
            raise RuntimeError("Another RevenueIQ refresh is running")
        try:
            stages = [
                ("acquire", [sys.executable, "scripts/download_data.py"]),
                ("validate_and_load", [sys.executable, "-m", "pipelines.ingest"]),
                (
                    "transform_and_test",
                    [
                        str(Path(sys.executable).parent / "dbt"),
                        "build",
                        "--project-dir",
                        "dbt",
                        "--profiles-dir",
                        "dbt",
                    ],
                ),
                ("analyze", [sys.executable, "-m", "analytics.run"]),
            ]
            log = []
            for name, command in stages:
                started = datetime.now(timezone.utc).isoformat()
                start = time.perf_counter()
                result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
                (reports / f"{name}.log").write_text(result.stdout + result.stderr)
                log.append(
                    {
                        "stage": name,
                        "started_at_utc": started,
                        "seconds": round(time.perf_counter() - start, 3),
                        "returncode": result.returncode,
                    }
                )
                (reports / "refresh_log.json").write_text(json.dumps(log, indent=2))
                print(f"{name}: {result.returncode} ({log[-1]['seconds']}s)", flush=True)
                if result.returncode:
                    raise RuntimeError(f"{name} failed; active release unchanged. See {reports / name}.log")
                if name == "transform_and_test":
                    with engine.begin() as conn:
                        tables = (
                            conn.execute(
                                text(
                                    "select table_name from information_schema.tables where table_schema=:schema and table_type='BASE TABLE'"
                                ),
                                {"schema": release},
                            )
                            .scalars()
                            .all()
                        )
                        for table in tables:
                            conn.execute(text(f"analyze {identifier(release)}.{identifier(table)}"))
                    shutil.copy2(ROOT / "dbt/target/run_results.json", reports / "dbt_run_results.json")
            publish(engine, release, reports)
            print(f"Published {release}", flush=True)
            # Convenience portfolio copies; the application reads versioned artifacts only.
            for file in reports.iterdir():
                if file.suffix in [".json", ".md", ".csv"]:
                    temporary = ROOT / "reports" / ("." + file.name + ".tmp")
                    shutil.copy2(file, temporary)
                    temporary.replace(ROOT / "reports" / file.name)
        finally:
            lock.execute(text("select pg_advisory_unlock(71401926)"))


if __name__ == "__main__":
    main()
