import os
import re
from datetime import timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS", "credits.json")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

TZ = timezone(timedelta(hours=3), "МСК")
DATETIME_FORMAT = "%d.%m.%Y %H:%M:%S"

SHEET_ORDERS = "Заявки"
SHEET_DICTS = "Справочники"
SHEET_JOURNAL = "Журнал"

COL_ID = "ID заявки"
COL_CREATED = "Создана"
COL_TG_ID = "Telegram ID"
COL_STATUS = "Статус"

JOURNAL_TIME = "Время"
JOURNAL_ACTION = "Действие"
ACTION_CREATED = "создал"
ACTION_UPDATED = "дополнил"
ACTION_DELETED = "удалил"

DICT_TYPE = "Тип"
DICT_SUBTYPE = "Подтип"
DICT_STATUS = "Статус"

STATUS_NEW = "Новая"

ID_PREFIX = "D-"
ID_DIGITS = 6
ID_RE = re.compile(rf"^{re.escape(ID_PREFIX)}(\d+)$")

RETRY_CODES = (429, 500, 502, 503)
RETRY_ATTEMPTS = 6
RETRY_DELAY = 2
RETRY_MAX_DELAY = 60
