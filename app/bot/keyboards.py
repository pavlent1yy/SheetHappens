from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app import texts


def _kb(rows: list[list[str]]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t) for t in row] for row in rows if row],
        resize_keyboard=True,
    )


def main_menu() -> ReplyKeyboardMarkup:
    return _kb([[texts.BTN_NEW, texts.BTN_MY], [texts.BTN_EDIT], [texts.BTN_DELETE]])


def choices(options: list[str], back: bool = True) -> ReplyKeyboardMarkup:
    rows = [options[i:i + 2] for i in range(0, len(options), 2)]
    rows.append([texts.BTN_BACK, texts.BTN_CANCEL] if back else [texts.BTN_CANCEL])
    return _kb(rows)


def step(skip: bool = False, back: bool = True) -> ReplyKeyboardMarkup:
    return choices([texts.BTN_SKIP] if skip else [], back)


def confirm() -> ReplyKeyboardMarkup:
    return _kb([[texts.BTN_SEND], [texts.BTN_RESTART, texts.BTN_CANCEL], [texts.BTN_BACK]])


def edit_fields() -> ReplyKeyboardMarkup:
    return choices([texts.BTN_FIELD_PHONE, texts.BTN_FIELD_COMMENT])


def yes_no() -> ReplyKeyboardMarkup:
    return _kb([[texts.BTN_YES, texts.BTN_NO]])


def owner_menu() -> ReplyKeyboardMarkup:
    return _kb([
        [texts.BTN_OWNER_STATS, texts.BTN_OWNER_ORDERS],
        [texts.BTN_OWNER_DICTS, texts.BTN_OWNER_PING],
        [texts.BTN_OWNER_EXIT],
    ])
