import re

SEPARATORS = re.compile(r"[\s\-()]")
INDIAN_MOBILE = re.compile(r"[6-9][0-9]{9}")


def normalise_phone(value: str) -> str:
    digits = SEPARATORS.sub("", value)
    if digits.startswith("+91"):
        digits = digits[3:]
    elif len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if not INDIAN_MOBILE.fullmatch(digits):
        raise ValueError("phone must be a 10-digit Indian mobile number")
    return digits
