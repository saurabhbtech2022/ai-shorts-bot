from app.overlay_text import build_scene_overlay, normalize_mixed_hindi
from app.prompts_loader import ScenePrompt


def test_normalize_mixed_hindi_ayodhya_caption() -> None:
    raw = "कushal nagari ayodhya raja dashrath ki rajdhani thi"
    out = normalize_mixed_hindi(raw)
    assert "अयोध्या" in out
    assert "दशरथ" in out
    assert "ayodhya" not in out.lower()


def test_build_scene_overlay_no_latin_tofu() -> None:
    scene = ScenePrompt(
        index=0,
        title_hindi="अyodhya rajya",
        image_prompt_en="Ancient Ayodhya city on Sarayu river",
        caption_hindi="कushal nagari ayodhya raja dashrath ki rajdhani thi",
    )
    overlay = build_scene_overlay(scene)
    assert len(overlay) > 10
    assert "अयोध्या" in overlay
    import re

    assert not re.search(r"[A-Za-z]", overlay)
