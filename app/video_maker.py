"""Build vertical Shorts video: slideshow (crossfade) or single-image Ken Burns."""

from __future__ import annotations

import random
import re
import subprocess
import sys
from pathlib import Path

from app.config import ASSETS_FONTS_DIR, MUSIC_DIR, Settings, get_settings
from app.logger import setup_logging

logger = setup_logging()

FONT_CANDIDATES = [
    ASSETS_FONTS_DIR / "NotoSansDevanagari-Regular.ttf",
    Path("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansDevanagari-Regular.ttf"),
    Path("/System/Library/Fonts/Supplemental/DevanagariMT.ttc"),
    Path("C:/Windows/Fonts/Nirmala.ttf"),
    Path("C:/Windows/Fonts/mangal.ttf"),
]


def resolve_devanagari_font() -> Path | None:
    """Return first existing Devanagari-capable font path."""
    for candidate in FONT_CANDIDATES:
        if candidate.is_file():
            return candidate
    bundled = list(ASSETS_FONTS_DIR.glob("*.ttf"))
    if bundled:
        return bundled[0]
    return None


def _escape_drawtext(text: str) -> str:
    escaped = text.replace("\\", "\\\\")
    escaped = escaped.replace(":", "\\:")
    escaped = escaped.replace("'", "\\'")
    escaped = escaped.replace("%", "\\%")
    escaped = escaped.replace("\n", " ")
    return escaped


def _escape_filter_path(path: Path) -> str:
    s = str(path.resolve())
    if sys.platform == "win32":
        s = s.replace("\\", "/").replace(":", "\\:")
    else:
        s = s.replace(":", "\\:")
    return s


def pick_random_music() -> Path | None:
    if not MUSIC_DIR.is_dir():
        return None
    files = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.MP3"))
    if not files:
        return None
    return random.choice(files)


def _ken_burns_chain(input_label: str, output_label: str, slide_seconds: int, fps: int) -> str:
    total_frames = slide_seconds * fps
    zoom_end = 1.12
    return (
        f"[{input_label}]scale=2160:3840:force_original_aspect_ratio=increase,"
        f"crop=2160:3840,"
        f"zoompan=z='min(zoom+0.0008,{zoom_end})':x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)':d={total_frames}:s=1080x1920:fps={fps}[{output_label}]"
    )


def _overlay_text_devanagari_only(text: str) -> str:
    """FFmpeg drawtext uses one font — strip Latin (Subscribe/Bell) that renders as boxes."""
    out = text.replace("Subscribe", "सब्सक्राइब").replace("subscribe", "सब्सक्राइब")
    out = out.replace("Bell icon", "").replace("—", " ").replace("-", " ")
    out = re.sub(r"[A-Za-z]+", "", out)
    return re.sub(r"\s+", " ", out).strip()


def _drawtext_enable_clauses(
    captions: list[str],
    slide_seconds: int,
    font_path: Path | None,
    enable_overlay: bool,
    output_duration: int = 15,
    hide_last_seconds: float = 0.0,
) -> str:
    if not enable_overlay or not captions:
        return ""
    font = font_path or resolve_devanagari_font()
    if not font:
        logger.warning("Devanagari font not found; skipping text overlay")
        return ""

    font_esc = _escape_filter_path(font)
    parts: list[str] = []
    for i, caption in enumerate(captions):
        if not caption.strip():
            continue
        text = _escape_drawtext(_overlay_text_devanagari_only(caption.strip())[:120])
        start = i * slide_seconds
        end = min(start + slide_seconds, float(output_duration))
        if hide_last_seconds > 0:
            end = min(end, max(start, float(output_duration) - hide_last_seconds))
        parts.append(
            f"drawtext=fontfile='{font_esc}':text='{text}':"
            f"fontcolor=white:fontsize=42:borderw=2:bordercolor=black@0.6:"
            f"x=(w-text_w)/2:y=h-th-280:box=1:boxcolor=black@0.45:boxborderw=12:"
            f"enable='between(t,{start},{end})'"
        )
    return ",".join(parts)


def _subscribe_cta_drawtext(
    output_duration: int,
    line1: str,
    line2: str,
    font_path: Path | None,
    cta_seconds: float,
) -> str:
    font = font_path or resolve_devanagari_font()
    if not font or not line1.strip():
        return ""
    font_esc = _escape_filter_path(font)
    start = max(0.0, output_duration - cta_seconds)
    end = float(output_duration)
    parts: list[str] = []
    t1 = _escape_drawtext(_overlay_text_devanagari_only(line1)[:80])
    parts.append(
        f"drawtext=fontfile='{font_esc}':text='{t1}':"
        f"fontcolor=yellow:fontsize=40:borderw=3:bordercolor=black@0.75:"
        f"x=(w-text_w)/2:y=h-th-200:box=1:boxcolor=red@0.55:boxborderw=14:"
        f"enable='between(t,{start},{end})'"
    )
    if line2.strip():
        t2 = _escape_drawtext(_overlay_text_devanagari_only(line2)[:80])
        parts.append(
            f"drawtext=fontfile='{font_esc}':text='{t2}':"
            f"fontcolor=white:fontsize=34:borderw=2:bordercolor=black@0.7:"
            f"x=(w-text_w)/2:y=h-th-130:box=1:boxcolor=black@0.5:boxborderw=10:"
            f"enable='between(t,{start},{end})'"
        )
    return ",".join(parts)


def _part_badge_drawtext(
    part_number: int,
    output_duration: int,
    font_path: Path | None,
    corner: str = "right",
) -> str:
    """Top-corner episode label (e.g. भाग 4840) for the full clip."""
    if part_number < 1:
        return ""
    font = font_path or resolve_devanagari_font()
    if not font:
        return ""
    font_esc = _escape_filter_path(font)
    text = _escape_drawtext(f"भाग {part_number}")
    corner_key = corner.strip().lower().replace("-", "_")
    if corner_key in ("left", "top_left", "topleft"):
        x_expr = "48"
    else:
        x_expr = "w-text_w-48"
    end = float(output_duration)
    return (
        f"drawtext=fontfile='{font_esc}':text='{text}':"
        f"fontcolor=white:fontsize=34:borderw=2:bordercolor=black@0.85:"
        f"x={x_expr}:y=68:box=1:boxcolor=black@0.6:boxborderw=10:"
        f"enable='between(t,0,{end})'"
    )


def build_slideshow_ffmpeg_command(
    image_paths: list[Path],
    output_path: Path,
    *,
    slide_seconds: int,
    crossfade_seconds: float,
    output_duration: int,
    captions: list[str],
    enable_text_overlay: bool,
    voiceover_path: Path | None,
    music_path: Path | None,
    font_path: Path | None,
    enable_subscribe_cta: bool = False,
    subscribe_cta_line1: str = "",
    subscribe_cta_line2: str = "",
    subscribe_cta_seconds: float = 4.0,
    enable_part_badge: bool = False,
    part_number: int | None = None,
    part_badge_corner: str = "right",
) -> list[str]:
    """Build ffmpeg argv for N-image slideshow with xfade crossfades."""
    fps = 25
    n = len(image_paths)
    if n == 0:
        raise ValueError("At least one image is required")

    cmd: list[str] = ["ffmpeg", "-y"]
    for img in image_paths:
        cmd.extend(["-loop", "1", "-i", str(img)])

    chains: list[str] = []
    for i in range(n):
        chains.append(_ken_burns_chain(f"{i}:v", f"v{i}", slide_seconds, fps))

    if n == 1:
        merged = "[v0]setpts=PTS-STARTPTS[vout]"
        filter_parts = chains + [merged]
    else:
        xfade_steps: list[str] = []
        prev = "v0"
        for i in range(1, n):
            out = f"vx{i}"
            offset = i * slide_seconds - i * crossfade_seconds
            xfade_steps.append(
                f"[{prev}][v{i}]xfade=transition=fade:duration={crossfade_seconds}:"
                f"offset={offset}[{out}]"
            )
            prev = out
        filter_parts = chains + xfade_steps
        merged = f"[{prev}]copy[vout]"
        filter_parts.append(merged)

    cta_tail = subscribe_cta_seconds if enable_subscribe_cta else 0.0
    overlay = _drawtext_enable_clauses(
        captions,
        slide_seconds,
        font_path,
        enable_text_overlay,
        output_duration=output_duration,
        hide_last_seconds=cta_tail,
    )
    subscribe = ""
    if enable_subscribe_cta:
        subscribe = _subscribe_cta_drawtext(
            output_duration,
            subscribe_cta_line1,
            subscribe_cta_line2,
            font_path,
            subscribe_cta_seconds,
        )
    part_badge = ""
    if enable_part_badge and part_number is not None:
        part_badge = _part_badge_drawtext(
            part_number,
            output_duration,
            font_path,
            part_badge_corner,
        )
    fade_out = max(0, output_duration - 0.5)
    video_fx = ",".join(x for x in (part_badge, overlay, subscribe) if x)
    if video_fx:
        filter_parts.append(f"[vout]{video_fx},fade=t=in:st=0:d=0.5,fade=t=out:st={fade_out}:d=0.5[vfinal]")
    else:
        filter_parts.append(
            f"[vout]fade=t=in:st=0:d=0.5,fade=t=out:st={fade_out}:d=0.5[vfinal]"
        )

    filter_complex = ";".join(filter_parts)

    audio_inputs: list[tuple[str, str]] = []
    base_idx = n
    if voiceover_path and voiceover_path.is_file():
        cmd.extend(["-i", str(voiceover_path)])
        audio_inputs.append((f"{base_idx}:a", "1.0"))
        base_idx += 1

    if music_path and music_path.is_file():
        cmd.extend(["-i", str(music_path)])
        audio_inputs.append((f"{base_idx}:a", "0.2"))
        base_idx += 1

    if audio_inputs:
        if len(audio_inputs) == 1:
            stream, vol = audio_inputs[0]
            fc = (
                f"{filter_complex};[{stream}]volume={vol},"
                f"apad=pad_dur={output_duration},atrim=0:{output_duration}[aout]"
            )
            cmd.extend(["-filter_complex", fc, "-map", "[vfinal]", "-map", "[aout]"])
        else:
            streams = []
            for i, (stream, vol) in enumerate(audio_inputs):
                streams.append(f"[{stream}]volume={vol}[a{i}]")
            mix_in = "".join(f"[a{i}]" for i in range(len(audio_inputs)))
            fc = (
                f"{filter_complex};"
                + ";".join(streams)
                + f";{mix_in}amix=inputs={len(audio_inputs)}:duration=longest:dropout_transition=2,"
                f"apad=pad_dur={output_duration},atrim=0:{output_duration}[aout]"
            )
            cmd.extend(["-filter_complex", fc, "-map", "[vfinal]", "-map", "[aout]"])
    else:
        cmd.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])
        cmd.extend(["-filter_complex", filter_complex, "-map", "[vfinal]", "-map", f"{n}:a"])

    cmd.extend(
        [
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(fps),
            "-t",
            str(output_duration),
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    return cmd


def build_ffmpeg_command(
    image_path: Path,
    output_path: Path,
    *,
    duration: int,
    caption_hindi: str,
    enable_text_overlay: bool,
    voiceover_path: Path | None,
    music_path: Path | None,
    font_path: Path | None,
) -> list[str]:
    """Single-image command (tests / legacy). Delegates to slideshow builder."""
    return build_slideshow_ffmpeg_command(
        [image_path],
        output_path,
        slide_seconds=duration,
        crossfade_seconds=0.0,
        output_duration=duration,
        captions=[caption_hindi],
        enable_text_overlay=enable_text_overlay,
        voiceover_path=voiceover_path,
        music_path=music_path,
        font_path=font_path,
    )


def make_video(
    image_paths: Path | list[Path],
    output_path: Path,
    caption_hindi: str | list[str],
    voiceover_path: Path | None = None,
    settings: Settings | None = None,
    part_number: int | None = None,
) -> Path:
    """
    Render MP4 Short from one or more stills (slideshow when len > 1).

    Raises:
        RuntimeError: FFmpeg failed.
    """
    settings = settings or get_settings()
    paths = [image_paths] if isinstance(image_paths, Path) else list(image_paths)
    if isinstance(caption_hindi, list):
        captions = caption_hindi
    else:
        captions = [caption_hindi] * len(paths)

    while len(captions) < len(paths):
        captions.append("")
    captions = captions[: len(paths)]

    music = pick_random_music()
    font = resolve_devanagari_font()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    slide_seconds = settings.scene_slide_seconds
    crossfade = settings.slideshow_crossfade_seconds
    duration = settings.video_duration

    cmd = build_slideshow_ffmpeg_command(
        paths,
        output_path,
        slide_seconds=slide_seconds,
        crossfade_seconds=crossfade if len(paths) > 1 else 0.0,
        output_duration=duration,
        captions=captions,
        enable_text_overlay=settings.enable_text_overlay,
        voiceover_path=voiceover_path,
        music_path=music,
        font_path=font,
        enable_subscribe_cta=settings.enable_subscribe_cta,
        subscribe_cta_line1=settings.subscribe_cta_overlay,
        subscribe_cta_line2=settings.subscribe_cta_overlay_sub,
        subscribe_cta_seconds=settings.subscribe_cta_seconds,
        enable_part_badge=settings.enable_part_badge,
        part_number=part_number,
        part_badge_corner=settings.part_badge_corner,
    )

    logger.info(
        "Running FFmpeg slideshow (%s images, %ss output, %ss per slide)",
        len(paths),
        duration,
        slide_seconds,
    )
    logger.debug(
        "FFmpeg command: %s",
        " ".join(re.sub(r"'([^']*)'", r"\1", p) if " " in p else p for p in cmd),
    )

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        logger.error("FFmpeg stderr: %s", result.stderr[-4000:])
        raise RuntimeError(f"FFmpeg failed with code {result.returncode}")

    if not output_path.is_file() or output_path.stat().st_size < 1000:
        raise RuntimeError("FFmpeg produced invalid or empty output")

    logger.info("Video saved to %s", output_path)
    return output_path
