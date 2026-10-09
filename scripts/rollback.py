"""Republish a previously validated retained release; never rebuild it in place."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text  # noqa: E402
from app.services import ENGINE  # noqa: E402
from pipelines.publication import publish  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("release")
    args = parser.parse_args()
    with ENGINE.connect() as conn:
        if not conn.scalar(text("select pg_try_advisory_lock(71401926)")):
            raise RuntimeError("Another refresh or rollback is running")
        try:
            exists = conn.scalar(
                text("select count(*) from revenueiq_meta.history where schema_name=:schema"), {"schema": args.release}
            )
            if not exists:
                raise ValueError("Only a previously published retained release may be restored")
            publish(ENGINE, args.release, Path(__file__).resolve().parents[1] / "reports/releases" / args.release)
        finally:
            conn.execute(text("select pg_advisory_unlock(71401926)"))
    print("Restored " + args.release)


if __name__ == "__main__":
    main()
