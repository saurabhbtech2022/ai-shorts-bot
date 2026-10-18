"""YouTube Data API v3 upload using OAuth refresh token."""

from __future__ import annotations

import random
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


def _build_title(scene_title: str) -> str:
    base = f"{scene_title} | Ramayan Mahabharat #Shorts"
    if len(base) <= 100:
        return base
    trimmed = scene_title[:70].rstrip()
    return f"{trimmed}... #Shorts"[:100]


def _build_description(caption_hindi: str, hashtags: str) -> str:
    lines = [
        caption_hindi,
        "",
        hashtags.strip(),
        "",
        "AI generated art · Automated devotional shorts for education and inspiration.",
        "Images: Pollinations.ai (Flux)",
    ]
    return "\n".join(lines)[:4900]


def _build_tags(scene_title: str) -> list[str]:
    base = [
        "Shorts",
        "Ramayan",
        "Mahabharat",
        "Hindu",
        "Itihas",
        "Bhagwan",
        "Krishna",
        "Ram",
        "AI art",
    ]
    words = [w for w in scene_title.replace("|", " ").split() if len(w) > 1]
    return list(dict.fromkeys(base + words[:15]))[:30]


def upload_video(
    video_path: Path,
    *,
    scene_title: str,
    caption_hindi: str,
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

    creds = _build_credentials(settings)
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    body: dict = {
        "snippet": {
            "title": _build_title(scene_title),
            "description": _build_description(caption_hindi, settings.channel_hashtags),
            "tags": _build_tags(scene_title),
            "categoryId": "22",
        },
        "status": {
            "privacyStatus": settings.privacy_status,
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
    logger.info("YouTube upload complete: video_id=%s", video_id)
    return video_id
