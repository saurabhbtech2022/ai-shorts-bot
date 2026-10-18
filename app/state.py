"""Persistent pipeline state in data/state.json with atomic writes."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

from app.config import STATE_FILE
from app.slots import ALL_SLOTS, normalize_slot


class StateError(RuntimeError):
    """State file or idempotency violation."""


def _default_state() -> dict[str, Any]:
    return {"index": 0, "last_run_date": None, "daily_slots": {}, "history": []}


def read_state(path: Path | None = None) -> dict[str, Any]:
    """Load state from JSON; return defaults if file missing or corrupt."""
    file_path = path or STATE_FILE
    if not file_path.is_file():
        return _default_state()
    try:
        with file_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return _default_state()

    if not isinstance(data.get("index"), int):
        data["index"] = 0
    if "last_run_date" not in data:
        data["last_run_date"] = None
    if not isinstance(data.get("history"), list):
        data["history"] = []
    if not isinstance(data.get("daily_slots"), dict):
        data["daily_slots"] = {}
    return data


def write_state(state: dict[str, Any], path: Path | None = None) -> None:
    """Atomically write state (temp file + rename)."""
    file_path = path or STATE_FILE
    file_path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        dir=file_path.parent,
        prefix=".state.",
        suffix=".tmp",
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp_path, file_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def _slots_for_date(state: dict[str, Any], run_date: date) -> list[str]:
    daily = state.get("daily_slots") or {}
    raw = daily.get(str(run_date), [])
    if not isinstance(raw, list):
        return []
    return [normalize_slot(s) for s in raw if isinstance(s, str)]


def should_skip_run(
    run_date: date,
    slot: str,
    force: bool = False,
    path: Path | None = None,
) -> bool:
    """
    Return True if this date+slot already uploaded successfully.

    When force is True, always returns False.
    """
    if force:
        return False
    slot_id = normalize_slot(slot)
    state = read_state(path)
    completed = _slots_for_date(state, run_date)
    return slot_id in completed


def advance_index(current_index: int, prompt_count: int, step: int = 1) -> int:
    """Next index after consuming ``step`` scenes, wrapping at prompt_count."""
    if prompt_count <= 0:
        raise StateError("prompt_count must be positive")
    if step <= 0:
        raise StateError("step must be positive")
    return (current_index + step) % prompt_count


def record_success(
    *,
    run_date: date,
    slot: str,
    index_used: int,
    title: str,
    video_id: str | None,
    prompt_count: int,
    scenes_consumed: int = 1,
    path: Path | None = None,
) -> dict[str, Any]:
    """Update state after successful pipeline run for one daily slot."""
    state = read_state(path)
    slot_id = normalize_slot(slot)
    date_key = str(run_date)

    daily: dict[str, list[str]] = dict(state.get("daily_slots") or {})
    slots_today = list(daily.get(date_key, []))
    if slot_id not in slots_today:
        slots_today.append(slot_id)
    daily[date_key] = slots_today

    entry = {
        "date": date_key,
        "slot": slot_id,
        "title": title,
        "video_id": video_id,
    }
    history: list[dict[str, Any]] = list(state.get("history") or [])
    history.append(entry)

    new_state = {
        "index": advance_index(index_used, prompt_count, step=scenes_consumed),
        "last_run_date": date_key,
        "daily_slots": daily,
        "history": history[-100:],
    }
    write_state(new_state, path)
    return new_state


def completed_slots_today(run_date: date, path: Path | None = None) -> list[str]:
    """Slots already uploaded on run_date."""
    state = read_state(path)
    done = _slots_for_date(state, run_date)
    return [s for s in ALL_SLOTS if s in done]


def set_index(index: int, path: Path | None = None) -> dict[str, Any]:
    """Set current prompt index (for skip/reset)."""
    state = read_state(path)
    state["index"] = max(0, index)
    write_state(state, path)
    return state


def bump_index(prompt_count: int, step: int = 1, path: Path | None = None) -> dict[str, Any]:
    """Skip scene(s) without uploading."""
    state = read_state(path)
    current = int(state.get("index", 0))
    state["index"] = advance_index(current, prompt_count, step=step)
    write_state(state, path)
    return state


def reset_state(path: Path | None = None) -> dict[str, Any]:
    """Reset index to 0; keep history and daily_slots."""
    state = read_state(path)
    state["index"] = 0
    write_state(state, path)
    return state
