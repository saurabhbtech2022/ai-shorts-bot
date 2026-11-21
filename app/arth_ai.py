"""Generate Hindi retention hook + verse meaning via Cloudflare Workers AI."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import httpx

from app.config import DATA_DIR, Settings, get_settings
from app.logger import setup_logging
from app.prompts_loader import ScenePrompt

logger = setup_logging()

CACHE_FILE = DATA_DIR / "arth_cache.json"
DEFAULT_LLM_MODEL = "@cf/meta/llama-3.1-8b-instruct"

_SYSTEM = (
    "You write Hindi YouTube Shorts scripts for Shri Ramcharitmanas. "
    "Return ONLY valid JSON with keys hook and arth. "
    "hook = 1 short curiosity line in Hindi (max 22 words) so viewers stay. "
    "arth = simple Hindi meaning/teaching of THIS verse (max 45 words). "
    "Do NOT repeat the verse/caption words. Explain the meaning in easy Hindi. "
    "No English. No markdown. No extra keys."
)


def _cache_key(scene: ScenePrompt) -> str:
    raw = f"{scene.index}|{scene.title_hindi}|{scene.caption_hindi}|{scene.image_prompt_en}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _load_cache() -> dict[str, Any]:
    if not CACHE_FILE.is_file():
        return {}
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_cache(cache: dict[str, Any]) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning("Could not write arth cache: %s", exc)


def _extract_english_gloss(image_prompt_en: str) -> str:
    text = image_prompt_en.strip()
    text = re.sub(
        r"^.*?,\s*(?:shloka|chaupai|doha|soratha)\s*,\s*",
        "",
        text,
        count=1,
        flags=re.I,
    )
    text = re.sub(r",\s*traditional Indian.*$", "", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip(" ,.")


def _parse_model_json(text: str) -> dict[str, str] | None:
    cleaned = text.strip()
    if cleaned.startswith("{") and "'hook'" in cleaned and '"hook"' not in cleaned:
        # Some models return Python-dict style single quotes.
        cleaned = cleaned.replace("'", '"')
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    # Prefer first {...} block
    match = re.search(r"\{.*\}", cleaned, flags=re.S)
    if not match:
        return None
    blob = match.group(0)
    data: Any
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        try:
            # Last resort for lightly malformed JSON / single quotes.
            fixed = blob.replace("'", '"')
            data = json.loads(fixed)
        except Exception:
            return None
    if not isinstance(data, dict):
        return None
    hook = str(data.get("hook") or "").strip()
    arth = str(data.get("arth") or data.get("meaning") or "").strip()
    if not hook or not arth:
        return None
    # Drop trailing truncated junk if model cut off mid-sentence.
    arth = re.sub(r"\s+", " ", arth).strip()
    hook = re.sub(r"\s+", " ", hook).strip()
    return {"hook": hook, "arth": arth}


def _shares_too_much(a: str, b: str, *, threshold: float = 0.5) -> bool:
    def norm(s: str) -> set[str]:
        t = re.sub(r"[^\w\u0900-\u097f]+", " ", s.lower(), flags=re.UNICODE)
        return set(t.split())

    ta, tb = norm(a), norm(b)
    if not ta or not tb:
        return False
    return len(ta & tb) / min(len(ta), len(tb)) >= threshold


def _call_cloudflare_llm(
    scene: ScenePrompt,
    settings: Settings,
) -> dict[str, str] | None:
    if not settings.cloudflare_configured:
        return None

    model = (settings.cf_llm_model or DEFAULT_LLM_MODEL).strip()
    gloss = _extract_english_gloss(scene.image_prompt_en)
    user = (
        f"Title: {scene.title_hindi}\n"
        f"Hindi caption (do not repeat): {scene.caption_hindi}\n"
        f"English gloss: {gloss}\n"
        "Write JSON: {\"hook\":\"...\",\"arth\":\"...\"}"
    )
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{settings.cf_account_id}"
        f"/ai/run/{model}"
    )
    headers = {"Authorization": f"Bearer {settings.cf_api_token}"}
    body = {
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user},
        ],
        "max_tokens": 220,
        "temperature": 0.4,
    }
    logger.info("Generating AI Hindi arth via Workers AI (%s)", model)
    with httpx.Client(timeout=settings.cloudflare_timeout_seconds) as client:
        resp = client.post(url, headers=headers, json=body)
        if resp.status_code >= 400:
            logger.warning("AI arth HTTP %s: %s", resp.status_code, resp.text[:240])
            return None
        payload = resp.json()
    result = payload.get("result") if isinstance(payload, dict) else None
    text = ""
    if isinstance(result, dict):
        text = str(result.get("response") or result.get("text") or "")
    elif isinstance(result, str):
        text = result
    parsed = _parse_model_json(text)
    if not parsed:
        logger.warning("AI arth parse failed: %s", text[:200])
        return None
    if _shares_too_much(parsed["arth"], scene.caption_hindi):
        logger.warning("AI arth too similar to caption; rejecting")
        return None
    return parsed


def generate_ai_hook_and_arth(
    scene: ScenePrompt,
    settings: Settings | None = None,
    *,
    use_cache: bool = True,
) -> dict[str, str] | None:
    """
    Return {"hook","arth"} from Cloudflare LLM, with disk cache.

    Returns None when AI is disabled/unavailable so caller can fall back.
    """
    settings = settings or get_settings()
    if not settings.enable_ai_arth:
        return None

    key = _cache_key(scene)
    cache = _load_cache() if use_cache else {}
    cached = cache.get(key)
    if isinstance(cached, dict) and cached.get("hook") and cached.get("arth"):
        return {"hook": str(cached["hook"]), "arth": str(cached["arth"])}

    try:
        generated = _call_cloudflare_llm(scene, settings)
    except Exception as exc:
        logger.warning("AI arth request failed: %s", exc)
        return None
    if not generated:
        return None

    cache[key] = generated
    _save_cache(cache)
    return generated
