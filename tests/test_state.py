"""Tests for state.json idempotency and index wrap."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from app import state as state_mod


@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "state.json"


def test_advance_index_wraps(state_file: Path) -> None:
    assert state_mod.advance_index(59, 60) == 0
    assert state_mod.advance_index(0, 60) == 1


def test_idempotency_per_slot_same_date(state_file: Path) -> None:
    state_mod.write_state(
        {
            "index": 3,
            "last_run_date": "2026-01-01",
            "daily_slots": {"2026-01-01": ["morning"]},
            "history": [],
        },
        state_file,
    )
    assert state_mod.should_skip_run(date(2026, 1, 1), "morning", force=False, path=state_file) is True
    assert state_mod.should_skip_run(date(2026, 1, 1), "afternoon", force=False, path=state_file) is False
    assert state_mod.should_skip_run(date(2026, 1, 1), "morning", force=True, path=state_file) is False


def test_record_success_updates_index_and_slot(state_file: Path) -> None:
    state_mod.write_state({"index": 0, "last_run_date": None, "daily_slots": {}, "history": []}, state_file)
    new_state = state_mod.record_success(
        run_date=date(2026, 2, 1),
        slot="morning",
        index_used=0,
        title="Test",
        video_id="abc123",
        prompt_count=60,
        path=state_file,
    )
    assert new_state["index"] == 1
    assert new_state["daily_slots"]["2026-02-01"] == ["morning"]
    data = json.loads(state_file.read_text(encoding="utf-8"))
    assert data["history"][-1]["video_id"] == "abc123"
    assert data["history"][-1]["slot"] == "morning"
