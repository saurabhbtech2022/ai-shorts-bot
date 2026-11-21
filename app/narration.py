"""Build engaging Hindi voice scripts: hook + distinct arth (no verse repeat)."""

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
    ("ayodhya", "अयोध्या धर्म और शांति की नगरी थी।"),
    ("dasharatha", "महाराज दशरथ न्याय और धर्म से राज्य चलाते थे।"),
    ("yajna", "यज्ञ से प्रजा और वंश की मंगल कामना की जाती थी।"),
    ("rama", "श्री राम धर्म, करुणा और सत्य के आदर्श हैं।"),
    ("sita", "माता सीता धर्म और साहस की मूर्ति हैं।"),
    ("lakshman", "लक्ष्मण जी की सेवा-भावना भाई-धर्म का आदर्श है।"),
    ("forest", "वनवास में भी सत्य और धर्म नहीं छूटना चाहिए।"),
    ("wedding", "राम-सीता विवाह धर्म और प्रेम का पावन मिलन है।"),
    ("exile", "वनवास स्वीकार करना धर्म के प्रति समर्पण है।"),
    ("hanuman", "हनुमान जी की भक्ति सेवा और शक्ति का संगम है।"),
    ("lanka", "लंका प्रसंग अधर्म पर धर्म की जीत सिखाता है।"),
    ("shiva bow", "शिव धनुष टूटना प्रभु की दिव्य शक्ति दिखाता है।"),
    ("dhanush", "धनुष तोड़ना श्री राम की कृपा और सामर्थ्य है।"),
    ("sage", "ऋषि-आशीर्वाद सच्चे मार्ग का दीपक है।"),
    ("saraswati", "सरस्वती का स्मरण विद्या और शुद्ध वाणी देता है।"),
    ("ganesha", "गणेश का स्मरण विघ्न हटाकर मंगल आरंभ कराता है।"),
    ("guru", "गुरु-कृपा बिना सच्ची समझ नहीं खुलती।"),
    ("bhavani", "श्रद्धा-विश्वास के बिना ईश्वर का अनुभव कठिन है।"),
]

# English meaning fragments → short Hindi teaching (order: longer phrases first).
_EN_TO_HI: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bi bow to\b", re.I), "मैं वंदना करता हूँ "),
    (re.compile(r"\bwithout whom\b", re.I), "जिनके बिना "),
    (re.compile(r"\beven the\b", re.I), "यहाँ तक कि "),
    (re.compile(r"\bcannot\b", re.I), "नहीं कर सकते "),
    (re.compile(r"\bdevotees?\b", re.I), "भक्त "),
    (re.compile(r"\bcompassion\b|\bcompassionate\b", re.I), "कृपा "),
    (re.compile(r"\bwisdom\b|\bwise\b", re.I), "ज्ञान "),
    (re.compile(r"\bfaith\b", re.I), "श्रद्धा "),
    (re.compile(r"\bbelief\b", re.I), "विश्वास "),
    (re.compile(r"\bpraise[sd]?\b|\bglories\b|\bglory\b", re.I), "महिमा "),
    (re.compile(r"\bvirtue[s]?\b", re.I), "गुण "),
    (re.compile(r"\bstory\b|\btale\b", re.I), "कथा "),
    (re.compile(r"\blord rama\b|\brama'?s?\b|\braghupati\b", re.I), "श्री राम "),
    (re.compile(r"\bsaraswati\b|\bvani\b", re.I), "सरस्वती "),
    (re.compile(r"\bganesha\b|\bvinayaka\b", re.I), "गणेश "),
    (re.compile(r"\bguru\b", re.I), "गुरु "),
    (re.compile(r"\bshiva\b|\bshankara\b", re.I), "शिव "),
    (re.compile(r"\bbrahma\b", re.I), "ब्रह्मा "),
    (re.compile(r"\bvedas?\b|\bvedic\b", re.I), "वेद "),
    (re.compile(r"\bkali\b", re.I), "कलियुग "),
    (re.compile(r"\bdeceit\b|\bdeceivers?\b|\bfalse\b", re.I), "छल "),
]

_MORAL_LINES = [
    "यही सीख है — अर्थ समझकर भक्ति करो, सिर्फ शब्द दोहराने से काम नहीं चलता।",
    "इस भाव को जीवन में उतारो, तभी कथा फल देती है।",
    "अगले भाग में और गहरा अर्थ आएगा — जुड़े रहिए।",
    "श्रद्धा से सुनो, और संदेश को हृदय में बसाओ।",
]

_EXTRA_SENTENCES = [
    "यह प्रसंग रामचरित मानस की अमर शिक्षा है।",
    "इससे धैर्य, त्याग और सच्चाई सीखने को मिलती है।",
    "जय श्री राम।",
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
    return "यह प्रसंग भक्ति और धर्म का गहरा संदेश देता है।"


def _hook_for_scene(scene: ScenePrompt) -> str:
    return _HOOKS[scene.index % len(_HOOKS)]


def _extract_english_meaning(image_prompt_en: str) -> str:
    """Pull the English gloss embedded in the image-prompt field."""
    text = image_prompt_en.strip()
    text = re.sub(
        r"^.*?,\s*(?:shloka|chaupai|doha|soratha)\s*,\s*",
        "",
        text,
        count=1,
        flags=re.I,
    )
    text = re.sub(
        r",\s*traditional Indian.*$",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(r"^Ramcharitmanas illustration,\s*", "", text, flags=re.I)
    text = re.sub(r"^[^,]*,\s*", "", text, count=1)  # drop kand label if still present
    return re.sub(r"\s+", " ", text).strip(" ,.")


def _normalize_for_overlap(text: str) -> str:
    t = text.lower()
    t = re.sub(r"[^\w\u0900-\u097f]+", " ", t, flags=re.UNICODE)
    return re.sub(r"\s+", " ", t).strip()


def _shares_too_much(a: str, b: str, *, threshold: float = 0.55) -> bool:
    """True if one string largely repeats the other (token overlap)."""
    ta = set(_normalize_for_overlap(a).split())
    tb = set(_normalize_for_overlap(b).split())
    if not ta or not tb:
        return False
    inter = len(ta & tb)
    return inter / min(len(ta), len(tb)) >= threshold


def _teaching_from_english(english: str) -> str | None:
    """Best-effort Hindi teaching line from the English gloss (not a literal dump)."""
    if not english or len(english) < 12:
        return None
    en = english.strip()
    lower = en.lower()

    # Intent templates — explain the POINT, don't recite the line again.
    if re.search(r"\bbow to\b|\bvenerat|\bworship\b|\bpraise\b", lower):
        return (
            "मतलब यह है कि सच्चे आदर और स्मरण से ही मंगल शुरू होता है — "
            "बिना विनय के ज्ञान अधूरा रहता है।"
        )
    if re.search(r"\bfaith\b|\bbelief\b", lower) and re.search(r"\bwithout\b", lower):
        return (
            "संदेश साफ़ है — श्रद्धा और विश्वास के बिना भीतर बैठे प्रभु का अनुभव नहीं होता।"
        )
    if re.search(r"\bguru\b|\bwisdom\b|\bgrace\b", lower):
        return (
            "अर्थ यह है कि गुरु-कृपा और सच्चा ज्ञान टेढ़े मार्ग को भी पूज्य बना देता है।"
        )
    if re.search(r"\bdevotee\b|\bcompassion\b|\bhumble\b|\baffection\b", lower):
        return (
            "मतलब — प्रभु भक्तों के लिए कृपालु हैं; शरणागति अपनाने वाले पर कभी क्रोध नहीं करते।"
        )
    if re.search(r"\bkali\b|\bdeceit\b|\bcrow\b|\bfalse\b|\bpretend\b", lower):
        return (
            "सीधा अर्थ — कलियुग में दिखावा बहुत है; सच्ची भक्ति कर्म से पहचानी जाती है, वेश से नहीं।"
        )
    if re.search(r"\bpoet\b|\bintellect\b|\bstory\b|\btell this story\b", lower):
        return (
            "भाव यह है कि तुलसीदास जी विनम्रता से कहते हैं — प्रभु की महिमा अपार है, बुद्धि छोटी है, फिर भी भक्ति से गाते हैं।"
        )
    if re.search(r"\bbridge\b|\bant\b|\briver\b", lower):
        return (
            "अर्थ आसान है — कठिन मार्ग पर भी जब धर्म-सेतु बन जाए, तो छोटा जीव भी पार हो जाता है।"
        )
    if re.search(r"\brain\b|\bpearl\b|\bpoem\b|\breflect", lower):
        return (
            "मतलब — जब मन में सद्विचार बरसें, तभी काव्य और जीवन दोनों मोती जैसे निखरते हैं।"
        )
    if re.search(r"\bnot this\b|\bneti\b|\bceaselessly sing\b|\bglories\b", lower):
        return (
            "संदेश — प्रभु की महिमा इतनी बड़ी है कि देवता और वेद भी पूरा नहीं गा पाते, फिर भी गाते रहते हैं।"
        )

    # Lightweight lexical hint → still a teaching line, not a translation dump.
    hints: list[str] = []
    for pattern, hi in _EN_TO_HI:
        if pattern.search(en) and hi.strip() not in hints:
            hints.append(hi.strip())
        if len(hints) >= 4:
            break
    if hints:
        joined = "、".join(hints[:3]).replace("、", " और ")
        return f"इस पंक्ति का भाव {joined} से जुड़ा है — समझकर सुनो, सिर्फ शब्द मत दोहराओ।"
    return None


def _build_arth_explanation(scene: ScenePrompt, caption: str) -> str:
    """
    Distinct Hindi meaning/teaching — must NOT re-read the same shloka/caption.
    """
    form = _verse_form_hi(scene.title_hindi)
    english = _extract_english_meaning(scene.image_prompt_en)
    context = _context_from_image_prompt(scene.image_prompt_en)
    taught = _teaching_from_english(english)

    if taught and not _shares_too_much(taught, caption):
        explanation = f"सरल हिंदी में अर्थ समझिए — {taught}"
    else:
        explanation = (
            f"सरल हिंदी में अर्थ समझिए — {context.rstrip('।')}।"
            f" इस {form} का असली संदेश यही है कि दिखावे से नहीं, भाव और आचरण से भक्ति सिद्ध होती है।"
        )

    # Final guard: if somehow still too similar to caption, force generic teaching.
    if _shares_too_much(explanation, caption, threshold=0.45):
        explanation = (
            f"सरल हिंदी में अर्थ समझिए — शब्दों को दोहराना पर्याप्त नहीं।"
            f" इस {form} का मतलब है कि हमें विनय, श्रद्धा और सच्चाई से जीवन जीना चाहिए।"
        )
    return _ensure_period(re.sub(r"\s+", " ", explanation).strip())


def build_scene_narration(scene: ScenePrompt, video_seconds: int = 28) -> str:
    """
    Order: hook → shlok/chaupai (caption) → AI Hindi arth → short moral.

    Hard target: keep speech sized for <=30s Shorts.
    Arth must explain meaning, not merely re-read the same caption.
    Optional ``narration_hindi`` from prompts.txt overrides everything.
    """
    custom = (scene.narration_hindi or "").strip()
    if custom:
        return custom

    # Clamp locally even if caller passes a higher value.
    video_seconds = max(1, min(30, int(video_seconds)))

    title = _title_for_speech(scene.title_hindi.strip())
    form = _verse_form_hi(scene.title_hindi)
    caption = _ensure_period(scene.caption_hindi.strip())
    # Keep verse speakable inside a Short.
    spoken_verse = caption
    if len(spoken_verse) > 110:
        spoken_verse = _ensure_period(spoken_verse[:107].rstrip(" ,;:—-") + "…")

    moral = _MORAL_LINES[scene.index % len(_MORAL_LINES)]
    kand = title.split("·")[0].strip() if "·" in title else "रामचरित मानस"

    from app.arth_ai import generate_ai_hook_and_arth
    from app.config import get_settings

    ai_bits = None
    try:
        ai_bits = generate_ai_hook_and_arth(scene, get_settings())
    except Exception:
        ai_bits = None

    if ai_bits:
        hook = _ensure_period(ai_bits["hook"])
        arth_body = ai_bits["arth"].strip()
        if arth_body.startswith("सरल"):
            arth = _ensure_period(arth_body)
        else:
            arth = _ensure_period(f"अब सरल हिंदी में अर्थ समझिए — {arth_body}")
    else:
        hook = _hook_for_scene(scene)
        arth = _build_arth_explanation(scene, caption)
        arth = arth.replace("सरल हिंदी में अर्थ समझिए", "अब सरल हिंदी में अर्थ समझिए", 1)

    # Leave room for subscribe CTA (~4s) inside the <=30s clip.
    speak_seconds = max(16, video_seconds - 4)
    max_chars = max(220, int(speak_seconds * CHARS_PER_SECOND * 1.02))
    min_chars = max(160, int(speak_seconds * CHARS_PER_SECOND * 0.82))

    # 1) hook  2) shlok  3) arth  4) moral
    intro = f"{kand} की यह पवित्र {form} सुनिए।"
    text = f"{hook} {intro} {spoken_verse} {arth}"
    text = re.sub(r"\s+", " ", text).strip()

    # If AI arth accidentally echoed the verse, force a distinct teaching line.
    if _shares_too_much(arth, spoken_verse, threshold=0.55):
        fallback = _build_arth_explanation(scene, caption).replace(
            "सरल हिंदी में अर्थ समझिए",
            "अब सरल हिंदी में अर्थ समझिए",
            1,
        )
        text = f"{hook} {intro} {spoken_verse} {fallback}"
        text = re.sub(r"\s+", " ", text).strip()

    if len(text) + len(moral) + 1 <= max_chars and not _shares_too_much(moral, caption):
        text = f"{text} {moral}"

    idx = 0
    while len(text) < min_chars and idx < len(_EXTRA_SENTENCES):
        extra = _EXTRA_SENTENCES[idx]
        if extra not in text and len(text) + len(extra) + 1 <= max_chars:
            text = f"{text} {extra}"
        idx += 1

    if "जय श्री राम" not in text and len(text) + 14 <= max_chars + 10:
        text = f"{text} जय श्री राम।"

    # Hard trim if too long — prefer keeping verse + start of arth.
    if len(text) > max_chars + 40:
        text = _ensure_period(text[: max_chars].rstrip(" ,;:—-") + "…")

    return re.sub(r"\s+", " ", text).strip()


def build_overlay_arth_line(scene: ScenePrompt, max_len: int = 96) -> str:
    """On-screen meaning — prefer AI arth, else rule-based teaching line."""
    from app.arth_ai import generate_ai_hook_and_arth
    from app.config import get_settings

    ai_bits = None
    try:
        ai_bits = generate_ai_hook_and_arth(scene, get_settings())
    except Exception:
        ai_bits = None

    if ai_bits and ai_bits.get("arth"):
        line = ai_bits["arth"].strip()
    else:
        arth = _build_arth_explanation(scene, scene.caption_hindi.strip())
        line = re.sub(r"^सरल हिंदी में अर्थ समझिए\s*[—\-–]?\s*", "", arth).strip()

    if len(line) > max_len - 6:
        line = line[: max_len - 8].rstrip() + "…"
    return f"अर्थ: {line}"[:max_len]


def append_narration_expansion(text: str, expansion_index: int) -> str:
    """Add one more on-topic sentence when TTS is still shorter than the video."""
    pool = _MORAL_LINES + _EXTRA_SENTENCES
    idx = expansion_index % len(pool)
    extra = pool[idx]
    if extra in text:
        idx = (idx + 1) % len(pool)
        extra = pool[idx]
    return f"{text} {extra}".strip()
