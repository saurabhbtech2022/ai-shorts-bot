#!/usr/bin/env python3
"""Diagnose Cloudflare Workers AI auth without printing secrets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    env = dotenv_values(ROOT / ".env")
    aid = (env.get("CF_ACCOUNT_ID") or "").strip()
    tok = (env.get("CF_API_TOKEN") or "").strip()

    print("CF_ACCOUNT_ID set:", bool(aid), "len:", len(aid))
    print("CF_API_TOKEN set:", bool(tok), "len:", len(tok), "prefix:", (tok[:5] + "…") if tok else "none")
    if not aid or not tok:
        print("Missing CF credentials in .env")
        return 1

    headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}

    with httpx.Client(timeout=90.0) as client:
        vr = client.get("https://api.cloudflare.com/client/v4/user/tokens/verify", headers=headers)
        print("\n=== tokens/verify (IP filter NOT applied) ===")
        print("HTTP", vr.status_code)
        vj = _safe_json(vr)
        print("success:", vj.get("success"))
        print("errors:", json.dumps(vj.get("errors"), ensure_ascii=False)[:500])
        result = vj.get("result") or {}
        print("result.status:", result.get("status"))
        print("result.id:", result.get("id"))
        print("expires_on:", result.get("expires_on") or result.get("not_after") or "(none in verify payload)")

        url = (
            f"https://api.cloudflare.com/client/v4/accounts/{aid}"
            f"/ai/run/@cf/black-forest-labs/flux-1-schnell"
        )
        # Match app payload exactly (flux-1-schnell rejects unknown fields like num_steps).
        ar = client.post(
            url,
            headers=headers,
            json={"prompt": "simple temple illustration, divine temple, cinematic"},
        )
        print("\n=== Workers AI flux-1-schnell (IP filter APPLIES) ===")
        print("HTTP", ar.status_code)
        print("content-type:", ar.headers.get("content-type", ""))
        aj = _safe_json(ar)
        if aj:
            print("success:", aj.get("success"))
            print("errors:", json.dumps(aj.get("errors"), ensure_ascii=False)[:700])
            if isinstance(aj.get("result"), dict):
                print("result keys:", list(aj["result"].keys())[:10])
        else:
            print("body:", ar.text[:500])

        acc = client.get(f"https://api.cloudflare.com/client/v4/accounts/{aid}", headers=headers)
        print("\n=== accounts/{id} ===")
        print("HTTP", acc.status_code)
        accj = _safe_json(acc)
        print("success:", accj.get("success"))
        print("errors:", json.dumps(accj.get("errors"), ensure_ascii=False)[:500])
        if accj.get("result"):
            print("account name:", (accj.get("result") or {}).get("name"))

    print("\n=== interpretation ===")
    _interpret(vr.status_code, vj, ar.status_code, aj)
    return 0


def _safe_json(resp: httpx.Response) -> dict:
    try:
        data = resp.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _interpret(verify_http: int, verify: dict, ai_http: int, ai: dict) -> None:
    v_errors = verify.get("errors") or []
    a_errors = ai.get("errors") or []
    a_codes = [e.get("code") for e in a_errors if isinstance(e, dict)]
    a_msgs = " ".join(str(e.get("message", "")) for e in a_errors if isinstance(e, dict)).lower()

    if verify_http == 200 and verify.get("success") and (verify.get("result") or {}).get("status") == "active":
        print("Token verify: ACTIVE (not expired / not revoked for verify endpoint).")
    elif verify_http in (401, 403) or not verify.get("success"):
        print("Token verify FAILED → expired, revoked, or wrong token. Recreate CF_API_TOKEN.")
        return
    else:
        print("Token verify unclear; check errors above.")

    if ai_http == 200 and (ai.get("success") is True or "image" in str(ai.get("result", "")).lower() or ai.get("result")):
        print("Workers AI: OK — local Cloudflare image generation works.")
        return

    if 9109 in a_codes or "cannot use the access token from location" in a_msgs:
        print("ROOT CAUSE: IP filtering (403/9109). Remove Client IP Address Filtering on the token.")
        return
    if ai_http == 401 or 10000 in a_codes:
        print("ROOT CAUSE: auth/permission. Token needs Workers AI permission on this account.")
        return
    if ai_http == 429 or any(c in a_codes for c in (429, 8115)):
        print("ROOT CAUSE: rate limit / quota exhausted.")
        return
    if ai_http == 403:
        print("ROOT CAUSE: 403 Forbidden on Workers AI — check IP filter, permission, or account scope.")
        print("Not a simple '30-day auto-expire' unless verify also failed.")
        return
    print(f"Workers AI failed HTTP {ai_http}. See errors JSON above.")


if __name__ == "__main__":
    raise SystemExit(main())
