"""Image generation: Cloudflare Workers AI primary with layered fallbacks."""

from __future__ import annotations

import base64
import binascii
import random
import time
from io import BytesIO
from collections.abc import Callable
from pathlib import Path
from urllib.parse import quote

import httpx
from PIL import Image, ImageDraw, ImageFont

from app.config import FALLBACK_IMAGES_DIR, Settings, get_settings
from app.logger import setup_logging

logger = setup_logging()

TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
ASPECT_W = 9
ASPECT_H = 16


class ImageGenerationError(Exception):
    """Provider could not return a usable image."""


class ImageClientError(ImageGenerationError):
    """Non-retriable 4xx response from a provider."""


def _is_valid_image_bytes(content: bytes, content_type: str | None = None) -> bool:
    if content_type and not content_type.lower().startswith("image/"):
        if "json" in content_type.lower():
            return False
    if len(content) < 1000:
        return False
    try:
        with Image.open(BytesIO(content)) as img:
            img.verify()
        with Image.open(BytesIO(content)) as img:
            img.load()
            return img.width > 0 and img.height > 0
    except Exception:
        return False


def center_crop_9_16_and_resize(img: Image.Image) -> Image.Image:
    """Center-crop to 9:16 then resize to 1080x1920."""
    rgb = img.convert("RGB")
    w, h = rgb.size
    target_ratio = ASPECT_W / ASPECT_H
    current_ratio = w / h if h else target_ratio

    if current_ratio > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        box = (left, 0, left + new_w, h)
    else:
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        box = (0, top, w, top + new_h)

    cropped = rgb.crop(box)
    return cropped.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)


def _save_processed_image(image_bytes: bytes, output_path: Path) -> Path:
    with Image.open(BytesIO(image_bytes)) as img:
        processed = center_crop_9_16_and_resize(img)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        processed.save(output_path, format="JPEG", quality=92)
    return output_path


def _decode_base64_image_payload(raw: str) -> bytes:
    cleaned = raw.strip()
    if cleaned.startswith("data:") and "," in cleaned:
        cleaned = cleaned.split(",", 1)[1]
    try:
        return base64.b64decode(cleaned, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ImageGenerationError("Invalid base64 image payload") from exc


def _extract_image_bytes_from_response(response: httpx.Response) -> bytes:
    content_type = (response.headers.get("content-type") or "").lower()
    if content_type.startswith("image/"):
        data = response.content
        if _is_valid_image_bytes(data, content_type):
            return data
        raise ImageGenerationError("Empty or invalid binary image response")

    if "json" in content_type or response.text[:1] in ("{", "["):
        payload = response.json()
        for key in ("image", "result"):
            node = payload.get(key)
            if isinstance(node, str):
                decoded = _decode_base64_image_payload(node)
                if _is_valid_image_bytes(decoded):
                    return decoded
            if isinstance(node, dict):
                for sub in ("image", "data", "b64_json"):
                    val = node.get(sub)
                    if isinstance(val, str):
                        decoded = _decode_base64_image_payload(val)
                        if _is_valid_image_bytes(decoded):
                            return decoded
        raise ImageGenerationError("JSON response did not contain a valid image")

    data = response.content
    if _is_valid_image_bytes(data, content_type):
        return data
    raise ImageGenerationError("Unrecognized image response format")


def _should_retry(exc: Exception) -> bool:
    if isinstance(exc, ImageClientError):
        return False
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if 400 <= code < 500:
            return False
        return 500 <= code < 600
    return True


def _fetch_cloudflare(prompt: str, settings: Settings) -> bytes:
    if not settings.cloudflare_configured:
        raise ImageGenerationError("Cloudflare Workers AI not configured")

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{settings.cf_account_id}"
        f"/ai/run/@cf/black-forest-labs/flux-1-schnell"
    )
    headers = {"Authorization": f"Bearer {settings.cf_api_token}"}
    body = {"prompt": prompt}

    logger.info("Fetching image from Cloudflare Workers AI (flux-1-schnell)")
    with httpx.Client(timeout=settings.cloudflare_timeout_seconds) as client:
        response = client.post(url, json=body, headers=headers)
        if response.status_code == 401:
            raise ImageClientError(
                "Cloudflare 401: token valid for verify but not for Workers AI. "
                "Recreate API token with Account resource = this account and "
                "permission Workers AI → Edit (or Read)."
            )
        if 400 <= response.status_code < 500:
            raise ImageClientError(
                f"Cloudflare client error {response.status_code}: {response.text[:300]}"
            )
        response.raise_for_status()
        return _extract_image_bytes_from_response(response)


def _pollinations_url(prompt: str, seed: int, settings: Settings) -> str:
    encoded = quote(prompt, safe="")
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={TARGET_WIDTH}&height={TARGET_HEIGHT}&model=flux&nologo=true&seed={seed}"
    )
    if settings.pollinations_api_key:
        url += f"&key={quote(settings.pollinations_api_key, safe='')}"
    return url


def _fetch_pollinations(prompt: str, settings: Settings, seed: int) -> bytes:
    url = _pollinations_url(prompt, seed, settings)
    logger.info("Fetching image from Pollinations (seed=%s)", seed)
    with httpx.Client(timeout=settings.pollinations_timeout_seconds, follow_redirects=True) as client:
        response = client.get(url)
        if 400 <= response.status_code < 500:
            raise ImageClientError(
                f"Pollinations client error {response.status_code}: {response.text[:200]}"
            )
        response.raise_for_status()
        if not _is_valid_image_bytes(response.content, response.headers.get("content-type")):
            raise ImageGenerationError("Invalid image response from Pollinations")
        return response.content


def _load_fallback_file_image() -> bytes | None:
    if not FALLBACK_IMAGES_DIR.is_dir():
        return None
    files = sorted(
        list(FALLBACK_IMAGES_DIR.glob("*.jpg"))
        + list(FALLBACK_IMAGES_DIR.glob("*.jpeg"))
        + list(FALLBACK_IMAGES_DIR.glob("*.png"))
        + list(FALLBACK_IMAGES_DIR.glob("*.webp"))
    )
    if not files:
        return None
    path = random.choice(files)
    data = path.read_bytes()
    if _is_valid_image_bytes(data):
        logger.info("Using fallback image file %s", path.name)
        return data
    return None


def _load_title_font(size: int = 52) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    from app.video_maker import resolve_devanagari_font

    path = resolve_devanagari_font()
    if path:
        try:
            return ImageFont.truetype(str(path), size)
        except OSError:
            pass
    for name in ("DejaVuSans.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _gradient_fallback(title: str) -> Image.Image:
    img = Image.new("RGB", (TARGET_WIDTH, TARGET_HEIGHT))
    draw = ImageDraw.Draw(img)
    for y in range(TARGET_HEIGHT):
        r = int(20 + (y / TARGET_HEIGHT) * 80)
        g = int(10 + (y / TARGET_HEIGHT) * 40)
        b = int(60 + (y / TARGET_HEIGHT) * 120)
        draw.line([(0, y), (TARGET_WIDTH, y)], fill=(r, g, b))

    font = _load_title_font(52)
    text = title[:80]
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (TARGET_WIDTH - tw) // 2
    y = (TARGET_HEIGHT - th) // 2
    pad = 16
    draw.rectangle(
        (x - pad, y - pad, x + tw + pad, y + th + pad),
        fill=(25, 25, 45),
    )
    draw.text((x, y), text, fill=(255, 235, 200), font=font)
    return img


def fetch_image_bytes(prompt: str, title: str, settings: Settings | None = None) -> bytes:
    """
    Try providers in order: Cloudflare → Pollinations (opt-in) → fallback files → gradient.

    Retries up to 4 times for retriable errors only (never retries 4xx).
    """
    settings = settings or get_settings()
    seed = random.randint(1, 2_147_483_647)
    providers: list[tuple[str, Callable[[], bytes]]] = []

    if settings.cloudflare_configured:
        providers.append(("cloudflare", lambda: _fetch_cloudflare(prompt, settings)))
    elif settings.cf_api_token and not settings.cf_account_id:
        logger.error(
            "CF_API_TOKEN set but CF_ACCOUNT_ID is empty — Workers AI will not run. "
            "Run: python scripts/get_cf_account_id.py or copy Account ID from "
            "Cloudflare Dashboard → Workers & Pages → Overview."
        )
    if settings.pollinations_enabled:
        providers.append(("pollinations", lambda: _fetch_pollinations(prompt, settings, seed)))

    if not providers:
        logger.warning(
            "No AI image providers configured (need CF_ACCOUNT_ID + CF_API_TOKEN; Pollinations is off)."
        )

    last_error: Exception | None = None

    for name, fetch_fn in providers:
        for attempt in range(4):
            try:
                data = fetch_fn()
                logger.info("Image provider succeeded: %s", name)
                return data
            except Exception as exc:
                last_error = exc
                if not _should_retry(exc):
                    logger.warning("Provider %s non-retriable error: %s", name, exc)
                    break
                logger.warning(
                    "Provider %s attempt %s failed: %s",
                    name,
                    attempt + 1,
                    exc,
                )
                time.sleep(min(2**attempt, 30))

    file_bytes = _load_fallback_file_image()
    if file_bytes:
        return file_bytes

    if not settings.cloudflare_configured:
        raise ImageGenerationError(
            "Cloudflare Workers AI not ready: set CF_ACCOUNT_ID in .env "
            "(Dashboard → Workers & Pages → Overview → Account ID). "
            "Pollinations is disabled."
        )

    raise ImageGenerationError(
        f"Cloudflare image generation failed after retries. Last error: {last_error}"
    )


def generate_image(
    prompt: str,
    title: str,
    output_path: Path,
    settings: Settings | None = None,
) -> Path:
    """Generate one vertical JPEG (1080x1920) and save to output_path."""
    settings = settings or get_settings()
    image_bytes = fetch_image_bytes(prompt, title, settings)
    return _save_processed_image(image_bytes, output_path)


def generate_scene_images(
    scenes: list[tuple[str, str, str]],
    output_dir: Path,
    settings: Settings | None = None,
) -> list[Path]:
    """
    Generate one image per scene tuple (english_prompt, hindi_title, unused).

    Files: image_01.jpg, image_02.jpg, ...
    """
    settings = settings or get_settings()
    paths: list[Path] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, (prompt_en, title_hindi, _) in enumerate(scenes, start=1):
        full_prompt = f"{prompt_en}{settings.image_style_suffix}"
        out = output_dir / f"image_{i:02d}.jpg"
        generate_image(full_prompt, title_hindi, out, settings)
        paths.append(out)
    return paths
