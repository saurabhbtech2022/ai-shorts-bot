from app.narration import build_scene_narration
from app.prompts_loader import ScenePrompt


def test_build_scene_narration_reaches_target_length() -> None:
    scene = ScenePrompt(
        index=0,
        title_hindi="बालकाण्ड",
        image_prompt_en="Ramcharitmanas mangalacharan",
        caption_hindi="वाणी और विनायक की मैं वन्दना करता हूँ।",
    )
    text = build_scene_narration(scene, video_seconds=15)
    assert "वाणी और विनायक" in text
    assert "जय श्री राम" in text
    assert len(text) >= 80


def test_custom_narration_field_used() -> None:
    custom = "यह पूरा पंद्रह सेकंड का कस्टम स्क्रिप्ट है। " * 3
    scene = ScenePrompt(
        index=0,
        title_hindi="t",
        image_prompt_en="x",
        caption_hindi="c",
        narration_hindi=custom,
    )
    assert build_scene_narration(scene, 15) == custom.strip()
