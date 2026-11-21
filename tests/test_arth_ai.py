from __future__ import annotations

import json

from app.arth_ai import _parse_model_json, generate_ai_hook_and_arth
from app.config import Settings
from app.prompts_loader import ScenePrompt


def test_parse_model_json_from_fenced_block() -> None:
    raw = """```json
{"hook": "रुकिए अर्थ सुनिए", "arth": "प्रभु भक्तों पर कृपा रखते हैं"}
```"""
    parsed = _parse_model_json(raw)
    assert parsed is not None
    assert "कृपा" in parsed["arth"]


def test_generate_ai_hook_and_arth_uses_llm(monkeypatch) -> None:
    scene = ScenePrompt(
        index=3,
        title_hindi="बालकाण्ड · दोहा 1 · chaupai",
        image_prompt_en=(
            "Ramcharitmanas illustration, बालकाण्ड, chaupai, "
            "The Lord is compassionate to devotees., "
            "traditional Indian divine art, cinematic, respectful, 9:16 vertical"
        ),
        caption_hindi="प्रभु भक्तों के हित के लिए कृपालु हैं।",
    )
    settings = Settings(
        CF_ACCOUNT_ID="acct",
        CF_API_TOKEN="tok",
        ENABLE_AI_ARTH="true",
        CF_LLM_MODEL="@cf/meta/llama-3.1-8b-instruct",
    )

    class _Resp:
        status_code = 200

        def json(self):
            return {
                "success": True,
                "result": {
                    "response": json.dumps(
                        {
                            "hook": "एक पल रुकिए अर्थ सुनिए",
                            "arth": "भगवान शरणागत भक्तों पर कभी क्रोध नहीं करते",
                        },
                        ensure_ascii=False,
                    )
                },
            }

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            return _Resp()

    monkeypatch.setattr("app.arth_ai.httpx.Client", _Client)
    out = generate_ai_hook_and_arth(scene, settings, use_cache=False)
    assert out is not None
    assert "शरणागत" in out["arth"]
    assert scene.caption_hindi.rstrip("।") not in out["arth"]
