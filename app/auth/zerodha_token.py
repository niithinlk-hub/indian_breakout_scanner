from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import requests

from app.config import get_settings


def build_login_url(api_key: str) -> str:
    """Build the Zerodha login URL for request-token generation."""

    return f"https://kite.zerodha.com/connect/login?v=3&api_key={api_key}"


def exchange_request_token(
    *,
    api_key: str,
    api_secret: str,
    request_token: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Exchange a request token for a Kite access token."""

    checksum = hashlib.sha256(f"{api_key}{request_token}{api_secret}".encode("utf-8")).hexdigest()
    response = requests.post(
        "https://api.kite.trade/session/token",
        headers={"X-Kite-Version": "3"},
        data={
            "api_key": api_key,
            "request_token": request_token,
            "checksum": checksum,
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "success":
        raise RuntimeError(f"Token exchange failed: {json.dumps(payload)}")
    return payload


def save_access_token(env_path: Path, access_token: str) -> None:
    """Persist the latest access token into the local .env file."""

    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    updated = False
    new_lines: list[str] = []
    for line in lines:
        if line.startswith("ZERODHA_ACCESS_TOKEN="):
            new_lines.append(f"ZERODHA_ACCESS_TOKEN={access_token}")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(f"ZERODHA_ACCESS_TOKEN={access_token}")
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def save_redirect_url(env_path: Path, redirect_url: str) -> None:
    """Persist the configured redirect URL into the local .env file."""

    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    updated = False
    new_lines: list[str] = []
    for line in lines:
        if line.startswith("ZERODHA_REDIRECT_URL="):
            new_lines.append(f"ZERODHA_REDIRECT_URL={redirect_url}")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(f"ZERODHA_REDIRECT_URL={redirect_url}")
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate and save Zerodha access tokens.")
    parser.add_argument("--redirect-url", help="The Zerodha app redirect URL.", default=None)
    parser.add_argument("--show-login-url", action="store_true", help="Print the Zerodha login URL.")
    parser.add_argument("--request-token", help="Exchange the given request token for an access token.")
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to the .env file where the access token should be stored.",
    )
    return parser


def _read_saved_redirect_url(env_path: Path) -> str:
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("ZERODHA_REDIRECT_URL="):
            return line.split("=", 1)[1].strip()
    return ""


def main() -> None:
    args = build_parser().parse_args()
    settings = get_settings()
    env_path = Path(args.env_file)
    redirect_url = args.redirect_url or _read_saved_redirect_url(env_path)

    if not settings.zerodha_api_key or not settings.zerodha_api_secret:
        raise RuntimeError("ZERODHA_API_KEY and ZERODHA_API_SECRET must be set in .env.")

    if args.redirect_url:
        save_redirect_url(env_path, args.redirect_url)

    if args.show_login_url:
        if not redirect_url:
            raise RuntimeError("Provide --redirect-url or set ZERODHA_REDIRECT_URL in .env first.")
        print(build_login_url(settings.zerodha_api_key))
        return

    if args.request_token:
        payload = exchange_request_token(
            api_key=settings.zerodha_api_key,
            api_secret=settings.zerodha_api_secret,
            request_token=args.request_token,
            timeout_seconds=settings.request_timeout_seconds,
        )
        access_token = str(payload["data"]["access_token"])
        save_access_token(env_path, access_token)
        print("Access token saved to .env")
        return

    raise RuntimeError("Use --show-login-url or --request-token.")


if __name__ == "__main__":
    main()
