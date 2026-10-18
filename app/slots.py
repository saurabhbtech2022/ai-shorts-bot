"""Daily upload slots: subah / dopahar / sham (morning / afternoon / evening)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

SLOT_MORNING = "morning"
SLOT_AFTERNOON = "afternoon"
SLOT_EVENING = "evening"

ALL_SLOTS: tuple[str, ...] = (SLOT_MORNING, SLOT_AFTERNOON, SLOT_EVENING)

SLOT_LABELS_HI: dict[str, str] = {
    SLOT_MORNING: "subah",
    SLOT_AFTERNOON: "dopahar",
    SLOT_EVENING: "sham",
}


def normalize_slot(slot: str) -> str:
    """Validate and normalize slot id."""
    key = slot.strip().lower()
    aliases = {
        "subah": SLOT_MORNING,
        "dopahar": SLOT_AFTERNOON,
        "sham": SLOT_EVENING,
        "shaam": SLOT_EVENING,
        "evening": SLOT_EVENING,
        "afternoon": SLOT_AFTERNOON,
        "morning": SLOT_MORNING,
        "noon": SLOT_AFTERNOON,
    }
    normalized = aliases.get(key, key)
    if normalized not in ALL_SLOTS:
        raise ValueError(
            f"Invalid slot {slot!r}; use one of: {', '.join(ALL_SLOTS)} "
            f"(or subah/dopahar/sham)"
        )
    return normalized


def infer_slot_from_clock(
    now: datetime,
    morning_hm: tuple[int, int],
    afternoon_hm: tuple[int, int],
    evening_hm: tuple[int, int],
) -> str:
    """
    Pick the slot whose scheduled time is closest at or before ``now`` (same calendar day).

    Before first slot → morning. After evening → evening.
    """
    minutes_now = now.hour * 60 + now.minute

    def to_min(hm: tuple[int, int]) -> int:
        return hm[0] * 60 + hm[1]

    points = [
        (to_min(morning_hm), SLOT_MORNING),
        (to_min(afternoon_hm), SLOT_AFTERNOON),
        (to_min(evening_hm), SLOT_EVENING),
    ]
    points.sort()
    chosen = points[0][1]
    for minute, slot_id in points:
        if minutes_now >= minute:
            chosen = slot_id
    return chosen
