import base64
import binascii
import json
from typing import Any

from assessment.ids import MAX_DB_ID

INVALID_CURSOR = "cursor is invalid"


def encode_cursor(last_id: int) -> str:
    raw = json.dumps({"id": last_id}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(token: Any) -> int:
    if not isinstance(token, str):
        raise ValueError(INVALID_CURSOR)
    try:
        payload = json.loads(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)))
    except (binascii.Error, ValueError) as exc:
        raise ValueError(INVALID_CURSOR) from exc
    last_id = payload.get("id") if isinstance(payload, dict) else None
    if not isinstance(last_id, int) or isinstance(last_id, bool) or not 0 < last_id <= MAX_DB_ID:
        raise ValueError(INVALID_CURSOR)
    return last_id
