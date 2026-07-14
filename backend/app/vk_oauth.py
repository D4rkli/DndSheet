import base64
import hashlib
import secrets
from urllib.parse import urlencode

import httpx

from .config import settings

# VK ID (OAuth 2.1 + PKCE) — the current VK auth protocol, replacing the
# legacy oauth.vk.com client_id/client_secret flow. "id.vk.ru" is VK's
# current host for this; "id.vk.com" is kept alive as a legacy alias.
VK_ID_HOST = "id.vk.ru"


def generate_pkce_pair() -> tuple[str, str]:
    """Returns (code_verifier, code_challenge) for the VK ID authorize request."""
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def build_vk_authorize_url(state: str, code_challenge: str) -> str:
    params = {
        "response_type": "code",
        "client_id": settings.VK_APP_ID,
        "redirect_uri": settings.VK_REDIRECT_URI,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "scope": "",
    }
    return f"https://{VK_ID_HOST}/authorize?{urlencode(params)}"


async def exchange_vk_code(code: str, state: str, code_verifier: str, device_id: str) -> dict:
    """Exchange an OAuth code for tokens (VK ID / OAuth 2.1 + PKCE), then fetch the profile.

    Returns {"vk_id", "first_name", "last_name", "username", "photo_url"}.
    Raises ValueError on any failure (bad code, VK API error, etc.).
    """
    async with httpx.AsyncClient(timeout=10) as client:
        token_res = await client.post(
            f"https://{VK_ID_HOST}/oauth2/auth",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": code_verifier,
                "client_id": settings.VK_APP_ID,
                "device_id": device_id,
                "redirect_uri": settings.VK_REDIRECT_URI,
                "state": state,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        )
        token_data = token_res.json()
        if "access_token" not in token_data or "user_id" not in token_data:
            raise ValueError(f"VK token exchange failed: {token_data}")

        access_token = token_data["access_token"]
        vk_id = token_data["user_id"]

        profile_res = await client.post(
            f"https://{VK_ID_HOST}/oauth2/user_info",
            data={
                "client_id": settings.VK_APP_ID,
                "access_token": access_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        )
        profile_data = profile_res.json()
        user = profile_data.get("user") or {}
        if not user:
            raise ValueError(f"VK profile fetch failed: {profile_data}")

    return {
        "vk_id": int(vk_id),
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "username": None,
        "photo_url": user.get("avatar"),
    }
