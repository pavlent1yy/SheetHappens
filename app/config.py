import os
import re
from datetime import timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS", "credits.json")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
PROXY_URL = os.getenv("PROXY_URL", "")

OWNER_USERNAME = os.getenv("OWNER_USERNAME", "").lstrip("@").lower()
OWNER_ENABLED = _bool("OWNER_ENABLED", True)

PHOTO_CHAT_ID = os.getenv("PHOTO_CHAT_ID", "")
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
PHOTOS_DIR = DATA_DIR / "photos"

DICTS_TTL = int(os.getenv("DICTS_TTL", "300"))
NOTIFY_INTERVAL = int(os.getenv("NOTIFY_INTERVAL", "15"))
ASSIGN_DELAY = int(os.getenv("ASSIGN_DELAY", "300"))
ASSIGN_INTERVAL = int(os.getenv("ASSIGN_INTERVAL", "30"))
MANAGERS_SPREADSHEET_ID = os.getenv("MANAGERS_SPREADSHEET_ID", "") or SPREADSHEET_ID

TZ = timezone(timedelta(hours=3), "МСК")
DATETIME_FORMAT = "%d.%m.%Y %H:%M:%S"

SHEET_ORDERS = "Заявки"
SHEET_DICTS = "Справочники"
SHEET_JOURNAL = "Журнал"
SHEET_MANAGERS = "Менеджеры"
SHEET_CONTROL = "Управление"

CONTROL_SEND_CELL = "B1"
CONTROL_SENT_AT_CELL = "B2"

COL_ID = "ID заявки"
COL_CREATED = "Создана"
COL_USERNAME = "Telegram"
COL_TG_ID = "Telegram ID"
COL_TYPE = "Тип"
COL_SUBTYPE = "Подтип"
COL_WEIGHT = "Вес, кг"
COL_PRICE = "Объявл. стоимость, ₽"
COL_FROM = "Откуда"
COL_TO = "Куда"
COL_COMMENT = "Комментарий"
COL_PHOTO = "Фото"
COL_PHONE = "Телефон получателя"
COL_STATUS = "Статус"
COL_MANAGER_COMMENT = "Комментарий менеджера"
COL_CLIENT_STATUS = "Статус для клиента"
COL_MANAGER = "Менеджер"
COL_ASSIGNED = "Назначена"

MGR_NAME = "Менеджер"
MGR_USERNAME = "Telegram"
MGR_TG_ID = "Telegram ID"
WEEKDAYS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")

JOURNAL_TIME = "Время"
JOURNAL_ACTION = "Действие"
ACTION_CREATED = "создал"
ACTION_UPDATED = "дополнил"
ACTION_DELETED = "удалил"

DICT_TYPE = "Тип"
DICT_SUBTYPE = "Подтип"
DICT_STATUS = "Статус"

STATUS_NEW = "Новая"
STATUS_ACCEPTED = "Принята"
EDITABLE_STATUSES = (STATUS_NEW, STATUS_ACCEPTED)
DELETABLE_STATUSES = (STATUS_NEW,)

ID_PREFIX = "D-"
ID_DIGITS = 6
ID_RE = re.compile(rf"^{re.escape(ID_PREFIX)}(\d+)$")

MAX_TEXT_LEN = 300
MY_ORDERS_LIMIT = 5
OWNER_ORDERS_LIMIT = 10
NO_USERNAME = "—"

RETRY_CODES = (429, 500, 502, 503)
RETRY_ATTEMPTS = 4
RETRY_DELAY = 1
RETRY_MAX_DELAY = 8
