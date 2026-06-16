"""Monthly auto-generation cron entry point.

Production wiring: a system cron at 03:00 UTC on the 1st runs::

    docker compose exec api python -m scripts.run_monthly_cron

For verification / pre-deploy::

    docker compose exec api python -m scripts.run_monthly_cron --dry
"""

from __future__ import annotations

import argparse
import json
import sys

from src.reports.cron import run_monthly


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--dry",
        action="store_true",
        help="List the (workspace, trainee, period) tuples without enqueueing.",
    )
    args = p.parse_args(argv)
    out = run_monthly(dry_run=args.dry)
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
