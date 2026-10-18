"""Tests for prompts.txt parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.prompts_loader import PromptsLoadError, load_prompts


def test_load_project_prompts() -> None:
    prompts = load_prompts()
    assert len(prompts) >= 6000
    assert prompts[0].title_hindi
    assert prompts[0].image_prompt_en
    assert prompts[0].caption_hindi


def test_invalid_line_raises(tmp_path: Path) -> None:
    bad = tmp_path / "prompts.txt"
    bad.write_text("only two | fields\n", encoding="utf-8")
    with pytest.raises(PromptsLoadError):
        load_prompts(bad)


def test_skip_comments_and_blanks(tmp_path: Path) -> None:
    good = tmp_path / "prompts.txt"
    good.write_text(
        "# comment\n\n"
        "शीर्षक | English prompt here | हिंदी कैप्शन\n",
        encoding="utf-8",
    )
    scenes = load_prompts(good)
    assert len(scenes) == 1
    assert scenes[0].title_hindi == "शीर्षक"
