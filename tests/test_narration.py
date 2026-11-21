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


def test_build_scene_narration_reads_verse_then_arth(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.arth_ai.generate_ai_hook_and_arth",
        lambda *args, **kwargs: None,
    )
    scene = _scene()
    text = build_scene_narration(scene, video_seconds=28)
    assert "सुनिए।" in text
    assert "वाणी और विनायक" in text
    assert "अब सरल हिंदी में अर्थ" in text or "सरल हिंदी में अर्थ" in text
    # Verse comes before the meaning section (hook may also say अर्थ)
    marker = "सरल हिंदी में अर्थ"
    assert text.index("वाणी और विनायक") < text.index(marker)


def test_build_scene_narration_uses_ai_when_available(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.arth_ai.generate_ai_hook_and_arth",
        lambda *args, **kwargs: {
            "hook": "रुकिए ये अर्थ दिल छू लेगा",
            "arth": "सरस्वती और गणेश का स्मरण मंगल और शुद्ध वाणी देता है",
        },
    )
    scene = _scene()
    text = build_scene_narration(scene, video_seconds=28)
    assert "दिल छू लेगा" in text
    assert "वाणी और विनायक की मैं वन्दना" in text  # shlok first
    assert "सरस्वती और गणेश का स्मरण" in text  # then arth
    assert text.index("वाणी और विनायक") < text.index("सरस्वती और गणेश का स्मरण")


def test_arth_section_is_not_only_caption_echo(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.arth_ai.generate_ai_hook_and_arth",
        lambda *args, **kwargs: None,
    )
    scene = _scene()
    arth = _build_arth_explanation(scene, scene.caption_hindi)
    assert not _shares_too_much(arth, scene.caption_hindi, threshold=0.5)


def test_custom_narration_field_used() -> None:
    custom = "यह पूरा पंद्रह सेकंड का कस्टम स्क्रिप्ट है। " * 3
    scene = _scene(narration_hindi=custom)
    assert build_scene_narration(scene, 28) == custom.strip()


def test_overlay_arth_line_prefixes_meaning(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.arth_ai.generate_ai_hook_and_arth",
        lambda *args, **kwargs: {
            "hook": "रुकिए",
            "arth": "राम धर्म के मार्ग से जीवन शुद्ध होता है",
        },
    )
    scene = _scene(
        index=1,
        title_hindi="बालकाण्ड · दोहा 1 · chaupai",
        caption_hindi="राम धर्म के मार्ग पर चलते हैं।",
    )
    line = build_overlay_arth_line(scene)
    assert line.startswith("अर्थ:")
    assert "राम धर्म के मार्ग पर चलते हैं" not in line


def test_video_seconds_hard_capped_at_30(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.arth_ai.generate_ai_hook_and_arth",
        lambda *args, **kwargs: {
            "hook": "रुकिए",
            "arth": "भक्ति समझ से फलती है",
        },
    )
    text = build_scene_narration(_scene(), video_seconds=90)
    assert len(text) < 28 * 13 * 1.35
