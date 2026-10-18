"""Core daily pipeline orchestration (CLI and FastAPI share this module)."""

from __future__ import annotations

import re
import shutil
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.config import OUTPUT_DIR, get_settings
from app.image_gen import generate_image, generate_scene_images
from app.logger import setup_logging
from app.prompts_loader import get_scene_at_index, get_scenes_from_index, load_prompts
from app.slots import SLOT_LABELS_HI, infer_slot_from_clock, normalize_slot
from app.state import read_state, record_success, should_skip_run
from app.narration import append_narration_expansion, build_scene_narration
from app.overlay_text import build_scene_overlay
from app.tts import generate_voiceover
from app.video_maker import make_video
from app.youtube import upload_video

logger = setup_logging()


def _parse_hh_mm(value: str) -> tuple[int, int]:
    parts = value.strip().split(":")
    hour, minute = int(parts[0]), int(parts[1])
    return hour, minute


def _today_in_tz() -> date:
    settings = get_settings()
    return datetime.now(ZoneInfo(settings.timezone)).date()


def _now_in_tz() -> datetime:
    settings = get_settings()
    return datetime.now(ZoneInfo(settings.timezone))


def resolve_run_slot(slot: str | None) -> str:
    """Use explicit slot or infer subah/dopahar/sham from clock."""
    if slot:
        return normalize_slot(slot)
    settings = get_settings()
    now = _now_in_tz()
    return infer_slot_from_clock(
        now,
        _parse_hh_mm(settings.upload_time_morning),
        _parse_hh_mm(settings.upload_time_afternoon),
        _parse_hh_mm(settings.upload_time_evening),
    )


def _output_dir_for(run_date: date, slot: str) -> Path:
    return OUTPUT_DIR / run_date.isoformat() / normalize_slot(slot)


def cleanup_old_outputs(keep_days: int = 7) -> None:
    """Remove output date folders older than keep_days."""
    if not OUTPUT_DIR.is_dir():
        return
    cutoff = _today_in_tz() - timedelta(days=keep_days)
    for child in OUTPUT_DIR.iterdir():
        if not child.is_dir():
            continue
        try:
            folder_date = date.fromisoformat(child.name)
        except ValueError:
            continue
        if folder_date < cutoff:
            shutil.rmtree(child, ignore_errors=True)
            logger.info("Removed old output folder %s", child)


def run_pipeline(
    dry_run: bool = False,
    force: bool = False,
    slot: str | None = None,
) -> dict[str, Any]:
    """
    One Short per call: 1 scene, 1 image, ``VIDEO_DURATION`` sec (default 5s).

    Run 3× per day with slots ``morning`` / ``afternoon`` / ``evening`` (subah/dopahar/sham).

    Args:
        dry_run: Skip YouTube upload and slot idempotency tracking.
        force: Run even if this date+slot already succeeded.
        slot: Daily slot id; inferred from clock if omitted.

    Returns:
        Result dict with status, title, paths, video_id, slot, timings.
    """
    settings = get_settings()
    run_date = _today_in_tz()
    slot_id = resolve_run_slot(slot)
    slot_hi = SLOT_LABELS_HI.get(slot_id, slot_id)
    started = time.perf_counter()
    result: dict[str, Any] = {
        "status": "started",
        "date": str(run_date),
        "slot": slot_id,
        "slot_label_hi": slot_hi,
        "dry_run": dry_run,
        "force": force,
        "title": None,
        "video_id": None,
        "video_path": None,
        "image_paths": [],
        "skipped": False,
        "message": None,
    }

    if should_skip_run(run_date, slot_id, force=force) and not dry_run:
        state = read_state()
        result["status"] = "skipped"
        result["skipped"] = True
        result["message"] = (
            f"Slot '{slot_id}' ({slot_hi}) already completed on {run_date}; use --force to override."
        )
        result["index"] = state.get("index")
        logger.info(result["message"])
        return result

    prompts = load_prompts()
    state = read_state()
    index = int(state.get("index", 0))
    scene_count = settings.scenes_per_run
    if scene_count <= 1:
        scene = get_scene_at_index(index)
        scenes = [scene]
    else:
        scenes = get_scenes_from_index(index, scene_count)

    result["index"] = scenes[0].index
    result["title"] = scenes[0].title_hindi if len(scenes) == 1 else " · ".join(s.title_hindi for s in scenes)
    logger.info(
        "Slot %s (%s) — scene %s/%s: %s",
        slot_id,
        slot_hi,
        scenes[0].index + 1,
        len(prompts),
        result["title"],
    )

    out_dir = _output_dir_for(run_date, slot_id)
    video_path = out_dir / "short.mp4"
    voice_path = out_dir / "voiceover.mp3"

    t0 = time.perf_counter()
    if len(scenes) == 1:
        scene = scenes[0]
        full_prompt = f"{scene.image_prompt_en}{settings.image_style_suffix}"
        image_path = out_dir / "image.jpg"
        generate_image(full_prompt, scene.title_hindi, image_path, settings)
        image_paths = [image_path]
    else:
        scene_tuples = [(s.image_prompt_en, s.title_hindi, s.caption_hindi) for s in scenes]
        image_paths = generate_scene_images(scene_tuples, out_dir, settings)

    logger.info("Image step took %.2fs (%s files)", time.perf_counter() - t0, len(image_paths))
    result["image_paths"] = [str(p) for p in image_paths]
    result["image_path"] = str(image_paths[0])

    captions = [s.caption_hindi for s in scenes]
    caption_text = captions[0] if len(captions) == 1 else " ".join(captions)
    overlay_texts = [build_scene_overlay(s) for s in scenes]
    overlay_for_video = overlay_texts[0] if len(overlay_texts) == 1 else overlay_texts
    if len(scenes) == 1:
        narration_text = build_scene_narration(scenes[0], settings.video_duration)
    else:
        narration_text = " ".join(
            build_scene_narration(s, settings.video_duration) for s in scenes
        )
    if settings.enable_subscribe_cta and settings.enable_voiceover:
        cta_voice = settings.subscribe_cta_voice.strip()
        if cta_voice and cta_voice not in narration_text:
            narration_text = re.sub(
                r"जय श्री राम, जय सीता राम।\s*$",
                "",
                narration_text,
            ).strip()
            narration_text = f"{narration_text} {cta_voice}".strip()

    voiceover_file: Path | None = None
    if settings.enable_voiceover:
        t0 = time.perf_counter()
        voiceover_file = generate_voiceover(
            narration_text,
            voice_path,
            float(settings.video_duration),
            expand_text=append_narration_expansion,
        )
        logger.info("TTS step took %.2fs", time.perf_counter() - t0)

    t0 = time.perf_counter()
    make_video(
        image_paths if len(image_paths) > 1 else image_paths[0],
        video_path,
        overlay_texts if len(scenes) > 1 else overlay_texts[0],
        voiceover_path=voiceover_file,
        settings=settings,
        part_number=scenes[0].index + 1,
    )
    logger.info("Video step took %.2fs", time.perf_counter() - t0)
    result["video_path"] = str(video_path)

    video_id: str | None = None
    if dry_run:
        result["status"] = "dry_run_complete"
        result["message"] = "Upload skipped (dry_run)"
        logger.info("Dry run complete for slot %s", slot_id)
    else:
        if not settings.youtube_configured:
            raise ValueError(
                "YouTube credentials not configured. Set YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN."
            )
        t0 = time.perf_counter()
        video_id = upload_video(
            video_path,
            scene_title=scenes[0].title_hindi,
            caption_hindi=caption_text,
            part_number=scenes[0].index + 1,
            image_prompt_en=scenes[0].image_prompt_en,
            settings=settings,
        )
        logger.info("Upload step took %.2fs", time.perf_counter() - t0)
        record_success(
            run_date=run_date,
            slot=slot_id,
            index_used=scenes[0].index,
            title=result["title"],
            video_id=video_id,
            prompt_count=len(prompts),
            scenes_consumed=len(scenes),
        )
        result["status"] = "success"
        result["video_id"] = video_id
        result["message"] = f"Uploaded to YouTube ({slot_hi})"

    cleanup_old_outputs(keep_days=7)

    result["elapsed_seconds"] = round(time.perf_counter() - started, 2)
    logger.info("Pipeline finished: %s", result["status"])
    return result
