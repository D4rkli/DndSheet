import hmac
import hashlib
from urllib.parse import parse_qsl

from .config import settings


def verify_telegram_init_data(init_data: str) -> dict:
    if not init_data:
        raise ValueError("Empty initData")

    data = dict(parse_qsl(init_data, keep_blank_values=True))

    if "hash" not in data:
        raise ValueError("No hash")

    hash_from_telegram = data.pop("hash")

    # секрет = sha256(bot_token)
    secret = hashlib.sha256(settings.BOT_TOKEN.encode()).digest()

    # формируем data_check_string
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(data.items())
    )

    hmac_hash = hmac.new(
        secret,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(hmac_hash, hash_from_telegram):
        raise ValueError("Bad Telegram initData")

    return data
