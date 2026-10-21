import re

from app import config
from app import texts

NUMBER_RE = re.compile(r"^\d+(,\d+)?$")
PHONE_RE = re.compile(r"^\+?[\d\s()-]+$")
LINK_RE = re.compile(r"https?://", re.IGNORECASE)


class ValidationError(Exception):
    pass


def text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValidationError(texts.ERR_EMPTY)
    if len(value) > config.MAX_TEXT_LEN:
        raise ValidationError(texts.ERR_TOO_LONG.format(limit=config.MAX_TEXT_LEN, length=len(value)))
    if LINK_RE.search(value):
        raise ValidationError(texts.ERR_LINK)
    return value


def number(value: str) -> str:
    value = text(value)
    if not NUMBER_RE.match(value):
        raise ValidationError(texts.ERR_NUMBER)
    if float(value.replace(",", ".")) <= 0:
        raise ValidationError(texts.ERR_NOT_POSITIVE)
    return value


def phone(value: str) -> str:
    value = text(value)
    digits = re.sub(r"\D", "", value)
    if not PHONE_RE.match(value) or not 10 <= len(digits) <= 15:
        raise ValidationError(texts.ERR_PHONE)
    return value
