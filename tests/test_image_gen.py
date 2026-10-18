"""Tests for 9:16 crop and fallback ordering helpers."""

from __future__ import annotations

from io import BytesIO

from PIL import Image

from app.image_gen import center_crop_9_16_and_resize


def test_center_crop_9_16_landscape() -> None:
    img = Image.new("RGB", (1920, 1080), color=(100, 100, 100))
    out = center_crop_9_16_and_resize(img)
    assert out.size == (1080, 1920)


def test_center_crop_9_16_portrait() -> None:
    img = Image.new("RGB", (800, 2000), color=(50, 50, 50))
    out = center_crop_9_16_and_resize(img)
    assert out.size == (1080, 1920)
