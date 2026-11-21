from app.narration import (
    _build_arth_explanation,
    _shares_too_much,
    build_overlay_arth_line,
    build_scene_narration,
)
from app.prompts_loader import ScenePrompt


def _scene(**kwargs) -> ScenePrompt:
    base = dict(
        index=0,
        title_hindi="बालकाण्ड · दोहा 0 · shloka",
        image_prompt_en=(
            "Ramcharitmanas illustration, बालकाण्ड, shloka, "
            "I bow to Saraswati and Ganesha, the givers of speech and auspicious beginnings., "
            "traditional Indian divine art, cinematic, respectful, 9:16 vertical"
        ),
        caption_hindi="वाणी और विनायक की मैं वन्दना करता हूँ।",
    )
    base.update(kwargs)
    return ScenePrompt(**base)


def test_build_scene_narration_has_hook_and_arth() -> None:
    text = build_scene_narration(_scene(), video_seconds=22)
    assert "सरल हिंदी में अर्थ" in text
    assert "जय श्री राम" in text
    assert len(text) >= 120
    assert text.index("रुकिए") < text.index("अर्थ") or "जानते हैं" in text or "पाठ" in text


def test_arth_does_not_repeat_caption() -> None:
    scene = _scene()
    text = build_scene_narration(scene, video_seconds=22)
    # Full caption must not be pasted again after speaking the cue.
    assert scene.caption_hindi.strip("।") not in text
    arth = _build_arth_explanation(scene, scene.caption_hindi)
    assert not _shares_too_much(arth, scene.caption_hindi, threshold=0.5)


def test_custom_narration_field_used() -> None:
    custom = "यह पूरा पंद्रह सेकंड का कस्टम स्क्रिप्ट है। " * 3
    scene = _scene(narration_hindi=custom)
    assert build_scene_narration(scene, 22) == custom.strip()


def test_overlay_arth_line_prefixes_meaning() -> None:
    scene = _scene(
        index=1,
        title_hindi="बालकाण्ड · दोहा 1 · chaupai",
        image_prompt_en=(
            "Ramcharitmanas illustration, बालकाण्ड, chaupai, "
            "Rama walks the path of dharma with compassion., "
            "traditional Indian divine art, cinematic, respectful, 9:16 vertical"
        ),
        caption_hindi="राम धर्म के मार्ग पर चलते हैं।",
    )
    line = build_overlay_arth_line(scene)
    assert line.startswith("अर्थ:")
    assert "राम धर्म के मार्ग पर चलते हैं" not in line
