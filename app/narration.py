"""Build ~15s Hindi voice scripts from scene metadata (no time-stretch filler)."""

from __future__ import annotations

import re

from app.prompts_loader import ScenePrompt

# ~14 chars/sec at TTS_RATE=+5% (natural Shorts pace, not slow-mo).
CHARS_PER_SECOND = 14

_MANAS_FILLERS = [
    "इन शब्दों में गोस्वामी तुलसीदास जी का भक्ति भाव है।",
    "श्रद्धा से श्रवण कीजिए, मन को शांति मिलेगी।",
    "जय श्री राम, जय सीता राम।",
]

_SCENE_CONTEXT: list[tuple[str, str]] = [
    ("ayodhya", "सरयू के तट पर अयोध्या कोसल की राजधानी थी, यहाँ धर्म और शांति का वास था।"),
    ("dasharatha", "महाराज दशरथ न्यायप्रिय और धर्मात्मा शासक थे, जिनका राज्य समृद्ध था।"),
    ("yajna", "यज्ञ की पवित्र अग्नि में प्रजा की भलाई और वंश की कामना की गई।"),
    ("rama", "भगवान श्री राम धर्म, करुणा और वीरता के प्रतीक हैं, जिनका चरित अमर है।"),
    ("sita", "माता सीता पतिव्रता और साहस की मूर्ति हैं, जो हर परीक्षा में धर्म नहीं छोड़तीं।"),
    ("lakshman", "लक्ष्मण जी ने भाई राम का साथ छोड़कर वन में भी सेवा का मार्ग चुना।"),
    ("forest", "वन की कठिन यात्रा में भी राम ने अहिंसा और सत्य का पालन किया।"),
    ("wedding", "राम और सीता का विवाह पावन संस्कारों से संपन्न हुआ, जगत ने आशीर्वाद दिया।"),
    ("exile", "चौदह वर्ष का वनवास राम ने शांत चित्त से स्वीकार किया, यही उनका धर्म था।"),
    ("hanuman", "हनुमान जी की भक्ति और शक्ति राम काज में अग्रणी रही।"),
    ("lanka", "लंका युद्ध में अधर्म पर धर्म की विजय हुई, यही रामायण का संदेश है।"),
    ("shiva bow", "शिव धनुष के टूटने से प्रभु की अलौकिक शक्ति का प्रमाण मिला।"),
    ("dhanush", "मिथिला में शिव धनुष रखा था, जिसे श्री राम ने भगवान की कृपा से तोड़ा।"),
    ("sage", "ऋषि मुनियों का आशीर्वाद और मार्गदर्शन राम के जीवन का आधार रहा।"),
]

_EXTRA_SENTENCES = [
    "यह प्रसंग श्री रामचरित मानस की अमर परंपरा का हिस्सा है।",
    "इस कथा से हमें धैर्य, त्याग और परिवार के प्रति कर्तव्य सीखने को मिलता है।",
    "श्रद्धा से सुनिए और जीवन में धर्म का मार्ग अपनाइए।",
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


def _context_from_image_prompt(image_prompt_en: str) -> str:
    lower = image_prompt_en.lower()
    for keyword, sentence in _SCENE_CONTEXT:
        if re.search(rf"\b{re.escape(keyword)}\b", lower):
            return sentence
    return "यह दृश्य रामचरित मानस के उसी पवित्र क्षण को दर्शाता है जिसे हम आज स्मरण करते हैं।"


def _build_manas_narration(caption: str, title: str, video_seconds: int) -> str:
    """~13–14s of speech at +5% rate — video ke adhe hisse mein khamoshi na rahe."""
    cap = _ensure_period(caption)
    kand_part = title.split("·")[0].strip() if "·" in title else "रामचरित मानस"
    kand_speech = _title_for_speech(kand_part)
    text = f"{kand_speech} की पवित्र पंक्ति। {cap}"
    target_chars = max(160, video_seconds * CHARS_PER_SECOND)
    for filler in _MANAS_FILLERS:
        if len(text) >= target_chars:
            break
        if filler not in text:
            text = f"{text} {filler}"
    return re.sub(r"\s+", " ", text).strip()


def build_scene_narration(scene: ScenePrompt, video_seconds: int = 15) -> str:
    """
    Hindi script long enough for natural TTS at normal speed (~video_seconds).

    Uses optional ``narration_hindi`` from prompts.txt (4th field) when set.
    """
    custom = (scene.narration_hindi or "").strip()
    if custom:
        return custom

    caption = _ensure_period(scene.caption_hindi.strip())
    if len(caption) >= 35:
        return _build_manas_narration(caption, scene.title_hindi.strip(), video_seconds)

    title = _title_for_speech(scene.title_hindi.strip())
    parts = [
        f"श्री रामचरित मानस की पावन गाथा — {title}।",
        caption,
    ]
    text = " ".join(p for p in parts if p)

    target_chars = max(120, video_seconds * CHARS_PER_SECOND)
    if len(caption) < 70 and len(text) < target_chars:
        context = _context_from_image_prompt(scene.image_prompt_en)
        if context and context not in text:
            text = f"{text} {context}"

    idx = 0
    while len(text) < target_chars and idx < len(_EXTRA_SENTENCES):
        text = f"{text} {_EXTRA_SENTENCES[idx]}"
        idx += 1

    return re.sub(r"\s+", " ", text).strip()


def append_narration_expansion(text: str, expansion_index: int) -> str:
    """Add one more on-topic sentence when TTS is still shorter than the video."""
    idx = expansion_index % len(_EXTRA_SENTENCES)
    extra = _EXTRA_SENTENCES[idx]
    if extra in text:
        idx = (idx + 1) % len(_EXTRA_SENTENCES)
        extra = _EXTRA_SENTENCES[idx]
    return f"{text} {extra}".strip()
