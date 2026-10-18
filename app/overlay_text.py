"""On-screen Hindi captions: short, readable Devanagari (no Roman mashup)."""

from __future__ import annotations

import re

from app.narration import _context_from_image_prompt, _ensure_period
from app.prompts_loader import ScenePrompt

# Common Ramayan names/tokens often written half in Roman in prompts.txt
_NAME_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"ayodhya", re.I), "अयोध्या"),
    (re.compile(r"dash?rath", re.I), "दशरथ"),
    (re.compile(r"\bram\b", re.I), "राम"),
    (re.compile(r"\bsita\b", re.I), "सीता"),
    (re.compile(r"laksh?man", re.I), "लक्ष्मण"),
    (re.compile(r"bharat", re.I), "भरत"),
    (re.compile(r"shatrughn", re.I), "शत्रुघ्न"),
    (re.compile(r"hanuman", re.I), "हनुमान"),
    (re.compile(r"ravana", re.I), "रावण"),
    (re.compile(r"vishw?amitr", re.I), "विश्वामित्र"),
    (re.compile(r"kaikeyi", re.I), "कैकेयी"),
    (re.compile(r"manthara", re.I), "मंथरा"),
    (re.compile(r"kosal", re.I), "कोसल"),
    (re.compile(r"kushal", re.I), "कोसल"),
    (re.compile(r"maharaj", re.I), "महाराज"),
    (re.compile(r"\braja\b", re.I), "राजा"),
]

_PARTICLE_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bki\b"), "की"),
    (re.compile(r"\bka\b"), "का"),
    (re.compile(r"\bke\b"), "के"),
    (re.compile(r"\bko\b"), "को"),
    (re.compile(r"\bse\b"), "से"),
    (re.compile(r"\bmein\b", re.I), "में"),
    (re.compile(r"\btha\b", re.I), "था"),
    (re.compile(r"\bthe\b", re.I), "थे"),
    (re.compile(r"\bthi\b", re.I), "थी"),
    (re.compile(r"\bhu[ae]\b", re.I), "हुआ"),
    (re.compile(r"\bhu[eé]\b", re.I), "हुए"),
]

OVERLAY_MAX_LEN = 96


def _latin_letter_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z]", text))


def normalize_mixed_hindi(text: str) -> str:
    """Turn prompts-style Roman+Hindi into readable Devanagari where possible."""
    out = text.strip()
    for pattern, repl in _NAME_REPLACEMENTS:
        out = pattern.sub(repl, out)
    for pattern, repl in _PARTICLE_REPLACEMENTS:
        out = pattern.sub(repl, out)
    # Drop leftover isolated Latin words (ffmpeg/font would show tofu boxes)
    out = re.sub(r"[A-Za-z]+", "", out)
    out = re.sub(r"\s+", " ", out).strip()
    return _ensure_period(out)


def build_scene_overlay(scene: ScenePrompt) -> str:
    """
    Short line(s) for video burn-in — must be understandable at a glance.

    Uses optional ``overlay_hindi`` on the scene when set; otherwise cleans caption
    or falls back to a scene-specific Hindi line from the image prompt.
    """
    custom = (scene.overlay_hindi or "").strip()
    if custom:
        return custom[:OVERLAY_MAX_LEN]

    caption = scene.caption_hindi.strip()
    if _latin_letter_count(caption) >= 4:
        cleaned = normalize_mixed_hindi(caption)
        if len(cleaned) >= 12 and _latin_letter_count(cleaned) == 0:
            return cleaned[:OVERLAY_MAX_LEN]
        context = _context_from_image_prompt(scene.image_prompt_en)
        title = normalize_mixed_hindi(scene.title_hindi)
        if title and len(title) < 40:
            line = f"{title} — {context}"
        else:
            line = context
        return line[:OVERLAY_MAX_LEN]

    return _ensure_period(caption)[:OVERLAY_MAX_LEN]
