import hmac
import hashlib
import time
from urllib.parse import parse_qsl

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from .config import settings

SESSION_COOKIE_NAME = "dnd_session"

_serializer = URLSafeTimedSerializer(settings.SESSION_SECRET, salt="dnd-session")


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

    return data


def verify_telegram_login_widget(data: dict) -> int:
    """Verify data from the Telegram Login Widget and return the tg user id.

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
    max_age = settings.SESSION_MAX_AGE_DAYS * 86400
    if auth_date <= 0 or time.time() - auth_date > max_age:
        raise ValueError("Telegram login data expired")

    return int(data["id"])


def create_session_cookie(tg_id: int) -> str:
    return _serializer.dumps({"tg_id": tg_id})


def read_session_cookie(token: str) -> int | None:
    if not token:
        return None
    max_age = settings.SESSION_MAX_AGE_DAYS * 86400
    try:
        data = _serializer.loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    tg_id = data.get("tg_id")
    return int(tg_id) if tg_id is not None else None
