"""APScheduler: three daily jobs (subah / dopahar / sham)."""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.logger import setup_logging
from app.pipeline import run_pipeline
from app.slots import SLOT_AFTERNOON, SLOT_EVENING, SLOT_MORNING

logger = setup_logging()

_scheduler: BackgroundScheduler | None = None


def _parse_hh_mm(value: str) -> tuple[int, int]:
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time: {value!r} (expected HH:MM)")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid time: {value}")
    return hour, minute


def _job_for_slot(slot: str) -> None:
    logger.info("Scheduler triggered pipeline slot=%s", slot)
    try:
        run_pipeline(dry_run=False, force=False, slot=slot)
    except Exception as exc:
        logger.exception("Scheduled pipeline failed (slot=%s): %s", slot, exc)


def start_scheduler() -> BackgroundScheduler:
    """Start three cron jobs; idempotent."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    settings = get_settings()
    tz = ZoneInfo(settings.timezone)

    schedule_map = [
        (SLOT_MORNING, settings.upload_time_morning),
        (SLOT_AFTERNOON, settings.upload_time_afternoon),
        (SLOT_EVENING, settings.upload_time_evening),
    ]

    _scheduler = BackgroundScheduler(timezone=tz)
    for slot_id, hhmm in schedule_map:
        hour, minute = _parse_hh_mm(hhmm)
        _scheduler.add_job(
            _job_for_slot,
            trigger=CronTrigger(hour=hour, minute=minute, timezone=tz),
            id=f"daily_shorts_{slot_id}",
            kwargs={"slot": slot_id},
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        logger.info(
            "Scheduled slot=%s at %02d:%02d %s",
            slot_id,
            hour,
            minute,
            settings.timezone,
        )

    _scheduler.start()
    return _scheduler


def stop_scheduler() -> None:
    """Shut down scheduler if running."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("APScheduler stopped")
