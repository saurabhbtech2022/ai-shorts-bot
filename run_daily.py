#!/usr/bin/env python3
"""CLI entrypoint for GitHub Actions and local cron."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env", override=True)

from app.config import get_settings
from app.logger import setup_logging
from app.pipeline import run_pipeline

get_settings.cache_clear()

logger = setup_logging()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run AI Shorts Bot — one 5s Short per slot (morning/afternoon/evening)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Generate media without YouTube upload")
    parser.add_argument("--force", action="store_true", help="Run even if this date+slot already uploaded")
    parser.add_argument(
        "--slot",
        type=str,
        default=None,
        help="Daily slot: morning|afternoon|evening (subah/dopahar/sham). Auto-detect if omitted.",
    )
    args = parser.parse_args()

    try:
        result = run_pipeline(dry_run=args.dry_run, force=args.force, slot=args.slot)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result.get("status") in ("success", "dry_run_complete", "skipped"):
            return 0
        return 1
    except Exception as exc:
        logger.exception("Pipeline failed")
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
