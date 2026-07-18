import hmac
import hashlib
import time
from urllib.parse import parse_qsl

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from .config import settings

SESSION_COOKIE_NAME = "dnd_session"

_serializer = URLSafeTimedSerializer(settings.SESSION_SECRET, salt="dnd-session")
_vk_state_serializer = URLSafeTimedSerializer(settings.SESSION_SECRET, salt="dnd-vk-state")


def verify_telegram_init_data(init_data: str) -> dict:
    if not init_data:
        raise ValueError("Empty initData")

    data = dict(parse_qsl(init_data, keep_blank_values=True))

    if "hash" not in data:
        raise ValueError("No hash")

    hash_from_telegram = data.pop("hash")

    # ✅ ВАЖНО: новый официальный способ
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=settings.BOT_TOKEN.encode(),
        digestmod=hashlib.sha256
    ).digest()

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(data.items())
    )

    hmac_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(hmac_hash, hash_from_telegram):
        raise ValueError("Bad Telegram initData")

    auth_date = int(data.get("auth_date", 0))
    if auth_date <= 0 or time.time() - auth_date > settings.TELEGRAM_AUTH_MAX_AGE_SECONDS:
        raise ValueError("Telegram initData expired")

    return data


def verify_telegram_login_widget(data: dict) -> dict:
    """Verify data from the Telegram Login Widget and return the tg profile.

    Uses the Login Widget signing scheme (secret = sha256(bot_token)),
    which is different from the WebApp initData scheme above.
    """
    data = dict(data)

    if "hash" not in data:
        raise ValueError("No hash")

    hash_from_telegram = data.pop("hash")

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(data.items()) if v is not None
    )

    secret_key = hashlib.sha256(settings.BOT_TOKEN.encode()).digest()

    hmac_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(hmac_hash, hash_from_telegram):
        raise ValueError("Bad Telegram login widget data")

    auth_date = int(data.get("auth_date", 0))
    if auth_date <= 0 or time.time() - auth_date > settings.TELEGRAM_AUTH_MAX_AGE_SECONDS:
        raise ValueError("Telegram login data expired")

    return {
        "tg_id": int(data["id"]),
        "first_name": data.get("first_name"),
        "last_name": data.get("last_name"),
        "username": data.get("username"),
        "photo_url": data.get("photo_url"),
    }


def create_session_cookie(
    provider: str,
    user_key: int,
    first_name: str | None = None,
    last_name: str | None = None,
    username: str | None = None,
    photo_url: str | None = None,
) -> str:
    return _serializer.dumps({
        "provider": provider,
        "user_key": user_key,
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
        "photo_url": photo_url,
    })


def read_session_cookie(token: str) -> dict | None:
    if not token:
        return None
    max_age = settings.SESSION_MAX_AGE_DAYS * 86400
    try:
        data = _serializer.loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    if data.get("provider") not in ("telegram", "vk") or data.get("user_key") is None:
        return None
    return data


VK_STATE_COOKIE_NAME = "dnd_vk_state"


def create_vk_state_cookie(state: str, code_verifier: str, device_id: str) -> str:
    return _vk_state_serializer.dumps({"state": state, "code_verifier": code_verifier, "device_id": device_id})


def read_vk_state_cookie(token: str) -> dict | None:
    """Returns {"state", "code_verifier", "device_id"} or None if missing/expired/tampered."""
    if not token:
        return None
    try:
        data = _vk_state_serializer.loads(token, max_age=600)  # 10 minutes to complete the VK redirect
    except (BadSignature, SignatureExpired):
        return None
    if "state" not in data or "code_verifier" not in data:
        return None
    return data
