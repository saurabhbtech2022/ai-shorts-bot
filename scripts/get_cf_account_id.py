#!/usr/bin/env python3
"""Print Cloudflare Account ID using API token (needs Account Read or list via zones)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import httpx


def main() -> int:
    token = os.environ.get("CF_API_TOKEN") or os.environ.get("CLOUDFLARE_API_TOKEN")
    env_file = PROJECT_ROOT / ".env"
    if not token and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("CF_API_TOKEN="):
                token = line.split("=", 1)[1].strip()
                break

    if not token:
        print("Set CF_API_TOKEN in .env or environment.", file=sys.stderr)
        return 1

    headers = {"Authorization": f"Bearer {token}"}
    verify = httpx.get(
        "https://api.cloudflare.com/client/v4/user/tokens/verify",
        headers=headers,
        timeout=30,
    )
    print("Token verify:", json.dumps(verify.json(), indent=2))

    for path in ("/accounts?per_page=50", "/zones?per_page=50"):
        resp = httpx.get(f"https://api.cloudflare.com/client/v4{path}", headers=headers, timeout=30)
        data = resp.json()
        print(f"\nGET {path} -> success={data.get('success')}")
        if path.startswith("/accounts") and data.get("result"):
            for acc in data["result"]:
                aid = acc.get("id")
                name = acc.get("name")
                print(f"  CF_ACCOUNT_ID={aid}  ({name})")
            return 0
        if path.startswith("/zones") and data.get("result"):
            for zone in data["result"]:
                aid = zone.get("account", {}).get("id")
                name = zone.get("name")
                if aid:
                    print(f"  CF_ACCOUNT_ID={aid}  (from zone {name})")
            if data.get("result"):
                return 0

    print(
        "\nCould not list Account ID with this token.\n"
        "Dashboard: Workers & Pages → Overview → copy Account ID (right sidebar).\n"
        "Then in .env: CF_ACCOUNT_ID=...\n"
        "Recreate API token with: Account → Account Settings → Read, Workers AI → Edit.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
