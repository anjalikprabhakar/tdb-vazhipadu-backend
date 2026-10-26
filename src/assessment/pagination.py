import base64
import binascii
import re
from typing import Any

from assessment.ids import MAX_DB_ID

INVALID_CURSOR = "cursor is invalid"
CURSOR_TOKEN = re.compile(r"[A-Za-z0-9_-]{1,28}")
CURSOR_ID = re.compile(r"[1-9][0-9]{0,18}")


def encode_cursor(last_id: int) -> str:
    return base64.urlsafe_b64encode(str(last_id).encode()).decode().rstrip("=")


def decode_cursor(token: Any) -> int:
    if not isinstance(token, str) or not CURSOR_TOKEN.fullmatch(token):
        raise ValueError(INVALID_CURSOR)
    padded = token + "=" * (-len(token) % 4)
    try:
        raw = base64.b64decode(padded, altchars=b"-_", validate=True).decode("ascii")
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise ValueError(INVALID_CURSOR) from exc
    if not CURSOR_ID.fullmatch(raw) or int(raw) > MAX_DB_ID:
        raise ValueError(INVALID_CURSOR)
    return int(raw)
