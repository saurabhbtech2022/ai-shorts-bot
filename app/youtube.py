"""YouTube Data API v3 upload using OAuth refresh token."""

from __future__ import annotations

import random
import re
import time
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from app.config import Settings, get_settings
from app.logger import setup_logging

logger = setup_logging()

YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
RETRIABLE_STATUS_CODES = {500, 502, 503, 504}

_KAND_EN: dict[str, str] = {
    "बालकाण्ड": "Bal Kand",
    "अयोध्याकाण्ड": "Ayodhya Kand",
    "अरण्यकाण्ड": "Aranya Kand",
    "किष्किन्धाकाण्ड": "Kishkindha Kand",
    "सुन्दरकाण्ड": "Sundar Kand",
    "लंकाकाण्ड": "Lanka Kand",
    "उत्तरकाण्ड": "Uttar Kand",
}

_STANZA_EN: dict[str, str] = {
    "doha": "Doha",
    "chaupai": "Chaupai",
    "shloka": "Shloka",
    "sortha": "Sortha",
}


def _build_credentials(settings: Settings) -> Credentials:
    if not settings.youtube_configured:
        raise ValueError("YouTube credentials missing (YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN)")
    creds = Credentials(
        token=None,
        refresh_token=settings.yt_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.yt_client_id,
        client_secret=settings.yt_client_secret,
        scopes=[YOUTUBE_UPLOAD_SCOPE],
    )
    creds.refresh(Request())
    return creds


def title_english_from_hindi(scene_title_hindi: str) -> str:
    """Mirror Hindi scene title (Kand · Doha N · type) in English."""
    parts = [p.strip() for p in scene_title_hindi.split("·")]
    if len(parts) < 2:
        return scene_title_hindi
    kand_hi = parts[0]
    kand_en = _KAND_EN.get(kand_hi, kand_hi)
    rest = parts[1:]
    out_parts = [kand_en]
    for seg in rest:
        m = re.match(r"दोहा\s*(\d+)", seg, re.IGNORECASE)
        if m:
            out_parts.append(f"Doha {m.group(1)}")
            continue
        low = seg.lower().strip()
        if low in _STANZA_EN:
            out_parts.append(_STANZA_EN[low])
        else:
            out_parts.append(seg)
    return " · ".join(out_parts)


def english_summary_from_prompt(image_prompt_en: str) -> str:
    """First English narrative line from the image prompt field."""
    chunks = [c.strip() for c in image_prompt_en.split(",")]
    if len(chunks) >= 4:
        return chunks[3]
    return ""


def _build_title(scene_title_hindi: str, part_number: int) -> str:
    title_en = title_english_from_hindi(scene_title_hindi)
    part_hi = f"भाग {part_number}"
    part_en = f"Part {part_number}"
    base = f"{part_hi} | {scene_title_hindi} | {part_en} | {title_en} | Ramcharitmanas #Shorts"
    if len(base) <= 100:
        return base
    short_hi = scene_title_hindi[:35].rstrip()
    short_en = title_en[:35].rstrip()
    compact = f"{part_hi} | {short_hi} | {part_en} | {short_en} #Shorts"
    return compact[:100].rstrip()


def _build_description(
    *,
    part_number: int,
    scene_title_hindi: str,
    scene_title_en: str,
    caption_hindi: str,
    english_summary: str,
    hashtags: str,
) -> str:
    lines = [
        f"भाग {part_number} · Part {part_number}",
        f"{scene_title_hindi}",
        f"{scene_title_en}",
        "",
        caption_hindi.strip(),
        "",
    ]
    if english_summary.strip():
        lines.extend([english_summary.strip(), ""])
    lines.extend(
        [
            hashtags.strip(),
            "",
            "श्री रामचरित मानस — गोस्वामी तुलसीदास | Sri Ramcharitmanas by Goswami Tulsidas",
            "AI-generated devotional art · Single-owner automated Short for education and inspiration.",
            "Images: Cloudflare Workers AI (Flux). Voice: Edge TTS (Hindi).",
            "",
            "Subscribe for the next part · अगले भाग के लिए सब्सक्राइब करें",
        ]
    )
    return "\n".join(lines)[:4900]


def _build_tags(scene_title_hindi: str, part_number: int) -> list[str]:
    title_en = title_english_from_hindi(scene_title_hindi)
    base = [
        "Shorts",
        "Ramcharitmanas",
        "Ramayan",
        "Tulsidas",
        "Hindu",
        "Itihas",
        "Bhakti",
        "Ram",
        "Sita",
        "Hanuman",
        f"Part {part_number}",
        f"भाग {part_number}",
    ]
    for src in (scene_title_hindi, title_en):
        words = [w.strip("·|,") for w in re.split(r"[\s·|]+", src) if len(w.strip("·|,")) > 1]
        base.extend(words)
    kand = scene_title_hindi.split("·")[0].strip()
    if kand in _KAND_EN:
        base.append(_KAND_EN[kand])
        base.append(kand)
    deduped = list(dict.fromkeys(base))
    return deduped[:30]


def upload_video(
    video_path: Path,
    *,
    scene_title: str,
    caption_hindi: str,
    part_number: int = 1,
    image_prompt_en: str = "",
    settings: Settings | None = None,
) -> str:
    """
    Resumable upload to YouTube; returns video ID.

    Raises:
        ValueError: Missing credentials or file.
        HttpError: Quota or auth failures (non-retriable).
        RuntimeError: Retries exhausted.
    """
    settings = settings or get_settings()
    if not video_path.is_file():
        raise ValueError(f"Video file not found: {video_path}")

    privacy = (settings.privacy_status or "public").strip().lower()
    if privacy not in ("public", "unlisted", "private"):
        privacy = "public"

    title_en = title_english_from_hindi(scene_title)
    english_summary = english_summary_from_prompt(image_prompt_en)

    creds = _build_credentials(settings)
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    body: dict = {
        "snippet": {
            "title": _build_title(scene_title, part_number),
            "description": _build_description(
                part_number=part_number,
                scene_title_hindi=scene_title,
                scene_title_en=title_en,
                caption_hindi=caption_hindi,
                english_summary=english_summary,
                hashtags=settings.channel_hashtags,
            ),
            "tags": _build_tags(scene_title, part_number),
            "categoryId": "22",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    body["status"]["containsSyntheticMedia"] = True

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=settings.youtube_upload_chunksize,
    )

    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    error: HttpError | None = None
    retry_count = 0
    max_retries = 8

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                logger.info("YouTube upload progress: %s%%", pct)
        except HttpError as exc:
            error = exc
            status_code = exc.resp.status if exc.resp else 0
            content = exc.content.decode("utf-8", errors="ignore") if exc.content else ""

            if status_code in (401, 403):
                logger.error("YouTube auth/forbidden (%s): %s", status_code, content[:500])
                raise
            if "quotaExceeded" in content or status_code == 403:
                logger.error("YouTube quota exceeded or forbidden")
                raise

            if status_code in RETRIABLE_STATUS_CODES and retry_count < max_retries:
                retry_count += 1
                sleep_s = random.uniform(2**retry_count, 2 ** (retry_count + 1))
                logger.warning(
                    "Retriable YouTube error %s; retry %s/%s in %.1fs",
                    status_code,
                    retry_count,
                    max_retries,
                    sleep_s,
                )
                time.sleep(sleep_s)
                continue
            raise
        except Exception as exc:
            if retry_count < max_retries:
                retry_count += 1
                sleep_s = random.uniform(1, 4)
                logger.warning("Upload chunk error: %s; retrying...", exc)
                time.sleep(sleep_s)
                continue
            raise RuntimeError(f"YouTube upload failed: {exc}") from exc

    if not response or "id" not in response:
        raise RuntimeError(f"YouTube upload failed: {error}")

    video_id = str(response["id"])
    logger.info("YouTube upload complete: video_id=%s privacy=%s", video_id, privacy)
    return video_id
