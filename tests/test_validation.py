import pytest

from app import config
from app.services import validation
from app.services.validation import ValidationError


@pytest.mark.parametrize("value", ["2", "2,5", " 1500 ", "0,1"])
def test_number_ok(value):
    assert validation.number(value) == value.strip()


@pytest.mark.parametrize("value", ["", "   ", "2.5", "2,5,1", "abc", "-3", "0", "0,0"])
def test_number_bad(value):
    with pytest.raises(ValidationError):
        validation.number(value)


@pytest.mark.parametrize("value", ["+7 900 123-45-67", "89001234567", "+7 (900) 123 45 67"])
def test_phone_ok(value):
    assert validation.phone(value) == value


@pytest.mark.parametrize("value", ["123", "+7 900 abc", "1" * 16])
def test_phone_bad(value):
    with pytest.raises(ValidationError):
        validation.phone(value)


def test_text_rejects_links():
    with pytest.raises(ValidationError):
        validation.text("смотри https://example.com")


def test_text_length_limit():
    assert validation.text("а" * config.MAX_TEXT_LEN)
    with pytest.raises(ValidationError):
        validation.text("а" * (config.MAX_TEXT_LEN + 1))
