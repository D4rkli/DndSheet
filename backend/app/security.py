import hmac
import hashlib
from urllib.parse import parse_qsl
from .config import settings

def verify_telegram_init_data(init_data: str) -> dict:
    """
    Возвращает dict с полями initData (в т.ч. user=JSON),
    если подпись валидна. Иначе кидает ValueError.
    """
    if not init_data:
        raise ValueError("No initData")

    data = dict(parse_qsl(init_data, keep_blank_values=True))
    hash_received = data.pop("hash", None)
    if not hash_received:
        raise ValueError("No hash")

    # data_check_string: ключи по алфавиту, формат key=value \n
    pairs = [f"{k}={data[k]}" for k in sorted(data.keys())]
    data_check_string = "\n".join(pairs)

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=settings.BOT_TOKEN.encode(),
        digestmod=hashlib.sha256,
    ).digest()

    hash_calc = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(hash_calc, hash_received):
        raise ValueError("Bad initData signature")

    return data
