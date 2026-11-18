from app.narration import build_overlay_arth_line, build_scene_narration
from app.prompts_loader import ScenePrompt


def test_build_scene_narration_has_hook_and_arth() -> None:
    scene = ScenePrompt(
        index=0,
        title_hindi="बालकाण्ड · दोहा 0 · shloka",
        image_prompt_en="Ramcharitmanas mangalacharan Saraswati Ganesha",
        caption_hindi="वाणी और विनायक की मैं वन्दना करता हूँ।",
    )
    text = build_scene_narration(scene, video_seconds=22)
    assert "वाणी और विनायक" in text
    assert "सरल हिंदी में अर्थ" in text
    assert "जय श्री राम" in text
    assert len(text) >= 160
    # Hook should appear near the start
    assert text.index("रुकिए") < text.index("अर्थ") or "जानते हैं" in text or "पाठ" in text


def test_custom_narration_field_used() -> None:
    custom = "यह पूरा पंद्रह सेकंड का कस्टम स्क्रिप्ट है। " * 3
    scene = ScenePrompt(
        index=0,
        title_hindi="t",
        image_prompt_en="x",
        caption_hindi="c",
        narration_hindi=custom,
    )
    assert build_scene_narration(scene, 22) == custom.strip()


def test_overlay_arth_line_prefixes_meaning() -> None:
    scene = ScenePrompt(
        index=1,
        title_hindi="बालकाण्ड · दोहा 1 · chaupai",
        image_prompt_en="rama ayodhya",
        caption_hindi="राम धर्म के मार्ग पर चलते हैं।",
    )
    line = build_overlay_arth_line(scene)
    assert line.startswith("अर्थ:")
    assert "राम धर्म" in line
