from urllib.parse import urlencode

import httpx

from .config import settings

VK_API_VERSION = "5.199"


def build_vk_authorize_url(state: str) -> str:
    params = {
        "client_id": settings.VK_APP_ID,
        "redirect_uri": settings.VK_REDIRECT_URI,
        "response_type": "code",
        "scope": "",
        "state": state,
        "v": VK_API_VERSION,
    }
    return f"https://oauth.vk.com/authorize?{urlencode(params)}"


async def exchange_vk_code(code: str) -> dict:
    """Exchange an OAuth code for an access token, then fetch the profile.

    Returns {"vk_id", "first_name", "last_name", "username", "photo_url"}.
    Raises ValueError on any failure (bad code, VK API error, etc.).
    """
    async with httpx.AsyncClient(timeout=10) as client:
        token_res = await client.get(
            "https://oauth.vk.com/access_token",
            params={
                "client_id": settings.VK_APP_ID,
                "client_secret": settings.VK_APP_SECRET,
                "redirect_uri": settings.VK_REDIRECT_URI,
                "code": code,
            },
        )
        token_data = token_res.json()
        if "access_token" not in token_data:
            raise ValueError(f"VK token exchange failed: {token_data}")

        access_token = token_data["access_token"]
        vk_id = token_data["user_id"]

        profile_res = await client.get(
            "https://api.vk.com/method/users.get",
            params={
                "user_ids": vk_id,
                "fields": "screen_name,photo_200",
                "access_token": access_token,
                "v": VK_API_VERSION,
            },
        )
        profile_data = profile_res.json()
        if "error" in profile_data:
            raise ValueError(f"VK profile fetch failed: {profile_data['error']}")

        profile = (profile_data.get("response") or [{}])[0]

    return {
        "vk_id": int(vk_id),
        "first_name": profile.get("first_name"),
        "last_name": profile.get("last_name"),
        "username": profile.get("screen_name"),
        "photo_url": profile.get("photo_200"),
    }
