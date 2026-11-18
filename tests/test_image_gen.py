"""Tests for 9:16 crop and fallback ordering helpers."""

from __future__ import annotations

import pytest
from PIL import Image

from app.config import Settings
from app.image_gen import (
    ImageGenerationError,
    _cloudflare_client_error_message,
    center_crop_9_16_and_resize,
    fetch_image_bytes,
)


def test_center_crop_9_16_landscape() -> None:
    img = Image.new("RGB", (1920, 1080), color=(100, 100, 100))
    out = center_crop_9_16_and_resize(img)
    assert out.size == (1080, 1920)


def test_center_crop_9_16_portrait() -> None:
    img = Image.new("RGB", (800, 2000), color=(50, 50, 50))
    out = center_crop_9_16_and_resize(img)
    assert out.size == (1080, 1920)


def test_cloudflare_9109_message_mentions_ip_filter() -> None:
    body = (
        '{"success":false,"errors":[{"code":9109,'
        '"message":"Cannot use the access token from location: 1.2.3.4"}]}'
    )
    msg = _cloudflare_client_error_message(403, body)
    assert "9109" in msg
    assert "IP" in msg


def test_fetch_image_bytes_fails_closed_without_providers() -> None:
    settings = Settings(
        CF_ACCOUNT_ID="",
        CF_API_TOKEN="",
        ENABLE_POLLINATIONS="false",
    )
    with pytest.raises(ImageGenerationError):
        fetch_image_bytes("prompt", "बालकाण्ड", settings)
