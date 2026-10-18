from app.video_maker import _overlay_text_devanagari_only


def test_strips_latin_subscribe() -> None:
    raw = "अगले भाग के लिए Subscribe करें"
    out = _overlay_text_devanagari_only(raw)
    assert "Subscribe" not in out
    assert "सब्सक्राइब" in out
