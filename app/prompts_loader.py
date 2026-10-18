"""Load and validate scene prompts from data/prompts.txt."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config import PROMPTS_FILE


@dataclass(frozen=True)
class ScenePrompt:
    """One scene: Hindi title, English image prompt, Hindi caption, optional narration."""

    index: int
    title_hindi: str
    image_prompt_en: str
    caption_hindi: str
    narration_hindi: str = ""
    overlay_hindi: str = ""


class PromptsLoadError(ValueError):
    """Raised when prompts.txt has invalid format or is empty."""


def _parse_line(line: str, line_number: int) -> tuple[str, str, str, str]:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        raise PromptsLoadError(f"Line {line_number}: empty or comment (use load_prompts to skip)")

    parts = [p.strip() for p in stripped.split("|")]
    if len(parts) not in (3, 4, 5):
        raise PromptsLoadError(
            f"Line {line_number}: expected 3–5 fields separated by '|', got {len(parts)}. "
            f"Format: Title | English prompt | Caption [| narration ~15s] [| on-screen Hindi]"
        )
    title, prompt_en, caption = parts[0], parts[1], parts[2]
    narration = parts[3] if len(parts) >= 4 else ""
    overlay = parts[4] if len(parts) == 5 else ""
    if not title or not prompt_en or not caption:
        raise PromptsLoadError(f"Line {line_number}: title, image prompt, and caption must be non-empty")
    return title, prompt_en, caption, narration, overlay


def load_prompts(path: Path | None = None) -> list[ScenePrompt]:
    """
    Read prompts file and return validated scene list.

    Args:
        path: Path to prompts.txt; defaults to project data/prompts.txt.

    Raises:
        PromptsLoadError: Invalid line format or no valid prompts.
        FileNotFoundError: File missing.
    """
    file_path = path or PROMPTS_FILE
    if not file_path.is_file():
        raise FileNotFoundError(f"Prompts file not found: {file_path}")

    scenes: list[ScenePrompt] = []
    with file_path.open(encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            title, prompt_en, caption, narration, overlay = _parse_line(raw, line_no)
            scenes.append(
                ScenePrompt(
                    index=len(scenes),
                    title_hindi=title,
                    image_prompt_en=prompt_en,
                    caption_hindi=caption,
                    narration_hindi=narration,
                    overlay_hindi=overlay,
                )
            )

    if not scenes:
        raise PromptsLoadError(f"No valid prompts in {file_path}")
    return scenes


def get_scene_at_index(index: int, path: Path | None = None) -> ScenePrompt:
    """Return scene at index, wrapping with modulo."""
    prompts = load_prompts(path)
    wrapped = index % len(prompts)
    scene = prompts[wrapped]
    return ScenePrompt(
        index=wrapped,
        title_hindi=scene.title_hindi,
        image_prompt_en=scene.image_prompt_en,
        caption_hindi=scene.caption_hindi,
        narration_hindi=scene.narration_hindi,
        overlay_hindi=scene.overlay_hindi,
    )


def get_scenes_from_index(
    start_index: int,
    count: int,
    path: Path | None = None,
) -> list[ScenePrompt]:
    """Return ``count`` consecutive scenes starting at start_index (wrapped)."""
    prompts = load_prompts(path)
    total = len(prompts)
    scenes: list[ScenePrompt] = []
    for offset in range(count):
        idx = (start_index + offset) % total
        base = prompts[idx]
        scenes.append(
            ScenePrompt(
                index=idx,
                title_hindi=base.title_hindi,
                image_prompt_en=base.image_prompt_en,
                caption_hindi=base.caption_hindi,
                narration_hindi=base.narration_hindi,
                overlay_hindi=base.overlay_hindi,
            )
        )
    return scenes
