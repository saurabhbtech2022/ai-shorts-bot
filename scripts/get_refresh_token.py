#!/usr/bin/env python3
"""
One-time OAuth flow to obtain YouTube upload refresh token.

Usage:
  1. Download OAuth client JSON from Google Cloud (Desktop app).
  2. export GOOGLE_OAUTH_CLIENT_SECRETS=/path/to/client_secret.json
     OR place client_secret*.json in project root.
  3. python scripts/get_refresh_token.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _find_client_secrets_file() -> Path:
    env_path = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRETS")
    if env_path:
        p = Path(env_path)
        if p.is_file():
            return p
        raise FileNotFoundError(f"GOOGLE_OAUTH_CLIENT_SECRETS not found: {p}")

    matches = sorted(PROJECT_ROOT.glob("client_secret*.json"))
    if matches:
        return matches[0]
    raise FileNotFoundError(
        "No client_secret*.json found. Set GOOGLE_OAUTH_CLIENT_SECRETS or place file in project root."
    )


def main() -> int:
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Install dependencies: pip install google-auth-oauthlib", file=sys.stderr)
        return 1

    secrets_file = _find_client_secrets_file()
    print(f"Using OAuth client file: {secrets_file}")

    flow = InstalledAppFlow.from_client_secrets_file(str(secrets_file), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    if not creds.refresh_token:
        print(
            "ERROR: No refresh token returned. Revoke app access in Google Account, "
            "set OAuth consent to In production, and run again with prompt=consent.",
            file=sys.stderr,
        )
        return 1

    with secrets_file.open(encoding="utf-8") as fh:
        data = json.load(fh)
    installed = data.get("installed") or data.get("web") or {}
    client_id = installed.get("client_id", "")
    client_secret = installed.get("client_secret", "")

    print("\n=== SUCCESS ===\n")
    print(f"YT_CLIENT_ID={client_id}")
    print(f"YT_CLIENT_SECRET={client_secret}")
    print(f"YT_REFRESH_TOKEN={creds.refresh_token}")
    print(
        "\nPaste the above into your local .env and GitHub Actions secrets "
        "(Settings → Secrets and variables → Actions).\n"
        "Keep refresh token private; never commit it.\n"
        "Tip: OAuth consent screen should be 'In production' so refresh token "
        "does not expire in 7 days (testing mode).\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
