"""Tests for FFmpeg command construction."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from app.video_maker import build_ffmpeg_command, build_slideshow_ffmpeg_command, make_video


def test_build_ffmpeg_command_contains_zoompan_and_drawtext() -> None:
    cmd = build_ffmpeg_command(
        Path("input.jpg"),
        Path("out.mp4"),
        duration=6,
        caption_hindi="जय श्री राम",
        enable_text_overlay=True,
        voiceover_path=None,
        music_path=None,
        font_path=Path("/fonts/NotoSansDevanagari-Regular.ttf"),
    )
    joined = " ".join(cmd)
    assert "zoompan" in joined
    assert "drawtext" in joined
    assert "libx264" in joined
    assert "1080x1920" in joined
    assert cmd[0] == "ffmpeg"


def test_slideshow_command_uses_xfade_for_three_images() -> None:
    cmd = build_slideshow_ffmpeg_command(
        [Path("a.jpg"), Path("b.jpg"), Path("c.jpg")],
        Path("out.mp4"),
        slide_seconds=5,
        crossfade_seconds=0.5,
        output_duration=15,
        captions=["एक", "दो", "तीन"],
        enable_text_overlay=True,
        voiceover_path=None,
        music_path=None,
        font_path=Path("/fonts/NotoSansDevanagari-Regular.ttf"),
    )
    joined = " ".join(cmd)
    assert "xfade" in joined
    assert joined.count("zoompan") == 3
    assert "-t 15" in joined or "-t" in joined


def test_subscribe_cta_drawtext_in_filter() -> None:
    cmd = build_slideshow_ffmpeg_command(
        [Path("a.jpg")],
        Path("out.mp4"),
        slide_seconds=15,
        crossfade_seconds=0.0,
        output_duration=15,
        captions=["कथा"],
        enable_text_overlay=True,
        voiceover_path=None,
        music_path=None,
        font_path=Path("/fonts/NotoSansDevanagari-Regular.ttf"),
        enable_subscribe_cta=True,
        subscribe_cta_line1="अगले भाग के लिए सब्सक्राइब करें",
        subscribe_cta_line2="घंटी दबाएँ",
        subscribe_cta_seconds=4.0,
    )
    joined = " ".join(cmd)
    assert "सब्सक्राइब" in joined
    assert "between(t,11.0,15" in joined or "between(t,11,15" in joined


def test_part_badge_drawtext_top_right() -> None:
    cmd = build_slideshow_ffmpeg_command(
        [Path("a.jpg")],
        Path("out.mp4"),
        slide_seconds=15,
        crossfade_seconds=0.0,
        output_duration=15,
        captions=["कथा"],
        enable_text_overlay=False,
        voiceover_path=None,
        music_path=None,
        font_path=Path("/fonts/NotoSansDevanagari-Regular.ttf"),
        enable_part_badge=True,
        part_number=42,
        part_badge_corner="right",
    )
    joined = " ".join(cmd)
    assert "भाग 42" in joined
    assert "w-text_w-48" in joined


def test_part_badge_corner_left() -> None:
    cmd = build_slideshow_ffmpeg_command(
        [Path("a.jpg")],
        Path("out.mp4"),
        slide_seconds=15,
        crossfade_seconds=0.0,
        output_duration=15,
        captions=[],
        enable_text_overlay=False,
        voiceover_path=None,
        music_path=None,
        font_path=Path("/fonts/NotoSansDevanagari-Regular.ttf"),
        enable_part_badge=True,
        part_number=1,
        part_badge_corner="left",
    )
    joined = " ".join(cmd)
    assert "x=48" in joined


@patch("app.video_maker.subprocess.run")
def test_make_video_invokes_ffmpeg(mock_run: MagicMock, tmp_path: Path) -> None:
    images = []
    for i in range(3):
        p = tmp_path / f"image_{i}.jpg"
        p.write_bytes(b"\xff\xd8\xff" + b"\x00" * 100)
        images.append(p)
    output = tmp_path / "short.mp4"

    def fake_run(cmd, **kwargs):
        output.write_bytes(b"0" * 2000)
        return MagicMock(returncode=0, stderr="")

    mock_run.side_effect = fake_run
    result = make_video(images, output, ["कैप्शन"] * 3, voiceover_path=None)
    assert result == output
    cmd = mock_run.call_args[0][0]
    assert "xfade" in " ".join(cmd)
