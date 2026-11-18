"""Build engaging Hindi voice scripts: hook + verse + simple arth (~16–25s)."""

from __future__ import annotations

import re

from app.prompts_loader import ScenePrompt

# Slightly slower sizing so arth + hook fit naturally without heavy speed-up.
CHARS_PER_SECOND = 13

_HOOKS = [
    "रुकिए — इस पंक्ति का अर्थ सुनकर मन बदल जाएगा।",
    "क्या आप जानते हैं तुलसीदास जी यहाँ सच में क्या कहना चाहते हैं?",
    "सिर्फ पाठ मत सुनिए — अर्थ समझिए, तभी भक्ति जीवंत होती है।",
    "आज की पंक्ति छोटी है, पर इसका संदेश जीवन बदल देने वाला है।",
    "एक पल रुककर सुनिए — यही अर्थ अक्सर लोग छोड़ देते हैं।",
    "अगर अर्थ समझ आए तो यह दोहा दिल में बस जाएगा।",
    "आगे बढ़ने से पहले यह सरल हिंदी अर्थ ज़रूर सुन लें।",
    "जो लोग अर्थ समझते हैं, वही कथा को पूरा जी पाते हैं।",
]

_SCENE_CONTEXT: list[tuple[str, str]] = [
    ("ayodhya", "सरयू के तट पर अयोध्या कोसल की राजधानी थी, जहाँ धर्म और शांति का वास था।"),
    ("dasharatha", "महाराज दशरथ न्यायप्रिय और धर्मात्मा शासक थे।"),
    ("yajna", "यज्ञ की पवित्र अग्नि में प्रजा की भलाई और वंश की कामना की गई।"),
    ("rama", "भगवान श्री राम धर्म, करुणा और वीरता के प्रतीक हैं।"),
    ("sita", "माता सीता पतिव्रता और साहस की मूर्ति हैं।"),
    ("lakshman", "लक्ष्मण जी ने भाई राम की सेवा को ही अपना धर्म माना।"),
    ("forest", "वन की कठिन यात्रा में भी राम ने सत्य और धर्म नहीं छोड़ा।"),
    ("wedding", "राम और सीता का विवाह पावन संस्कारों से संपन्न हुआ।"),
    ("exile", "चौदह वर्ष का वनवास राम ने शांत चित्त से स्वीकार किया।"),
    ("hanuman", "हनुमान जी की भक्ति और शक्ति राम काज में अग्रणी रही।"),
    ("lanka", "लंका युद्ध में अधर्म पर धर्म की विजय हुई।"),
    ("shiva bow", "शिव धनुष टूटने से प्रभु की अलौकिक शक्ति प्रकट हुई।"),
    ("dhanush", "मिथिला में शिव धनुष को श्री राम ने कृपा से तोड़ा।"),
    ("sage", "ऋषि-मुनियों का आशीर्वाद रामचरित का आधार रहा।"),
    ("saraswati", "वाणी और विद्या की देवी सरस्वती का स्मरण मंगल का आरंभ है।"),
    ("ganesha", "विघ्नहर्ता गणेश का स्मरण हर शुभ कार्य से पहले किया जाता है।"),
    ("guru", "गुरु की कृपा से ही सच्ची समझ और भक्ति खुलती है।"),
    ("bhavani", "श्रद्धा और विश्वास के बिना ईश्वर का साक्षात्कार कठिन है।"),
]

_MORAL_LINES = [
    "यही संदेश है — बिना समझ की भक्ति अधूरी रह जाती है।",
    "इस अर्थ को जीवन में उतारिए, तभी कथा फल देती है।",
    "अगले भाग में और गहराई आएगी — जुड़े रहिए।",
    "श्रद्धा से सुनिए, और अर्थ को हृदय में बसाइए।",
]

_EXTRA_SENTENCES = [
    "यह प्रसंग श्री रामचरित मानस की अमर परंपरा का हिस्सा है।",
    "इस कथा से हमें धैर्य, त्याग और परिवार के प्रति कर्तव्य मिलता है।",
    "श्रद्धा से सुनिए और धर्म का मार्ग अपनाइए।",
    "जय श्री राम, जय सीता राम।",
]


def _ensure_period(text: str) -> str:
    t = text.strip()
    if not t:
        return t
    if t[-1] in "।.!?":
        return t
    return t + "।"


def _title_for_speech(title: str) -> str:
    """Avoid English verse labels in TTS."""
    repl = {
        "shloka": "श्लोक",
        "chaupai": "चौपाई",
        "doha": "दोहा",
        "soratha": "सोरठा",
    }
    out = title
    for en, hi in repl.items():
        out = re.sub(en, hi, out, flags=re.I)
    return out


def _verse_form_hi(title: str) -> str:
    # prompts.txt uses "… · दोहा 12 · chaupai" — last segment is the real form.
    tail = title.split("·")[-1].strip().lower() if "·" in title else title.lower()
    if "chaupai" in tail or "चौपाई" in tail:
        return "चौपाई"
    if "soratha" in tail or "सोरठा" in tail:
        return "सोरठा"
    if "shloka" in tail or "श्लोक" in tail:
        return "श्लोक"
    if "doha" in tail or "दोहा" in tail:
        return "दोहा"
    return "पंक्ति"


def _context_from_image_prompt(image_prompt_en: str) -> str:
    lower = image_prompt_en.lower()
    for keyword, sentence in _SCENE_CONTEXT:
        if re.search(rf"\b{re.escape(keyword)}\b", lower):
            return sentence
    return "यह दृश्य रामचरित मानस के उसी पवित्र भाव को दर्शाता है।"


def _hook_for_scene(scene: ScenePrompt) -> str:
    return _HOOKS[scene.index % len(_HOOKS)]


def _build_arth_explanation(scene: ScenePrompt, caption: str, *, already_spoken: bool) -> str:
    """Conversational Hindi meaning so viewers stay and understand."""
    context = _context_from_image_prompt(scene.image_prompt_en)
    form = _verse_form_hi(scene.title_hindi)
    core = caption.strip()
    if core.endswith("।"):
        core = core[:-1].strip()

    if already_spoken or len(core) > 90:
        # Do not re-read the same long line — explain the feeling/teaching.
        explanation = (
            f"सरल हिंदी में अर्थ समझिए — {context.rstrip('।')}।"
            f" इस {form} का भाव यही है कि भक्ति और समझ साथ चलें।"
        )
    else:
        explanation = (
            f"सरल हिंदी में अर्थ — {core}।"
            f" यानी {context.rstrip('।')}।"
        )
    return re.sub(r"\s+", " ", explanation).strip()


def build_scene_narration(scene: ScenePrompt, video_seconds: int = 22) -> str:
    """
    Hook + verse/caption + Hindi arth, sized for ~video_seconds of natural TTS.

    Uses optional ``narration_hindi`` from prompts.txt (4th field) when set.
    """
    custom = (scene.narration_hindi or "").strip()
    if custom:
        return custom

    title = _title_for_speech(scene.title_hindi.strip())
    form = _verse_form_hi(scene.title_hindi)
    caption = _ensure_period(scene.caption_hindi.strip())
    spoken_caption = caption
    if len(spoken_caption) > 100:
        spoken_caption = _ensure_period(spoken_caption[:97].rstrip(" ,;:—-") + "…")

    hook = _hook_for_scene(scene)
    arth = _build_arth_explanation(
        scene,
        caption,
        already_spoken=len(caption) > 90,
    )
    moral = _MORAL_LINES[scene.index % len(_MORAL_LINES)]
    kand = title.split("·")[0].strip() if "·" in title else "रामचरित मानस"

    # ~0.85–1.05× clip length → natural pace on 16–25s Shorts.
    max_chars = max(220, int(video_seconds * CHARS_PER_SECOND * 1.05))
    min_chars = max(170, int(video_seconds * CHARS_PER_SECOND * 0.85))

    text = (
        f"{hook} {kand} की यह पवित्र {form} सुनिए। "
        f"{spoken_caption} {arth}"
    )
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) + len(moral) + 1 <= max_chars:
        text = f"{text} {moral}"

    idx = 0
    while len(text) < min_chars and idx < len(_EXTRA_SENTENCES):
        extra = _EXTRA_SENTENCES[idx]
        if extra not in text and len(text) + len(extra) + 1 <= max_chars:
            text = f"{text} {extra}"
        idx += 1

    if "जय श्री राम" not in text and len(text) + 14 <= max_chars + 10:
        text = f"{text} जय श्री राम।"

    return re.sub(r"\s+", " ", text).strip()


def build_overlay_arth_line(scene: ScenePrompt, max_len: int = 96) -> str:
    """Short on-screen meaning line for retention."""
    caption = scene.caption_hindi.strip()
    if not caption:
        return "अर्थ सुनिए — अंत तक रुकिए।"
    core = caption if len(caption) <= max_len - 6 else caption[: max_len - 8].rstrip() + "…"
    line = f"अर्थ: {core}"
    return line[:max_len]


def append_narration_expansion(text: str, expansion_index: int) -> str:
    """Add one more on-topic sentence when TTS is still shorter than the video."""
    pool = _MORAL_LINES + _EXTRA_SENTENCES
    idx = expansion_index % len(pool)
    extra = pool[idx]
    if extra in text:
        idx = (idx + 1) % len(pool)
        extra = pool[idx]
    return f"{text} {extra}".strip()
