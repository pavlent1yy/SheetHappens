import asyncio
import functools
import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any, ParamSpec, TypeVar

import gspread
from gspread.exceptions import APIError
from gspread.utils import ValueInputOption, rowcol_to_a1
from requests.exceptions import ConnectionError, Timeout

from app import config

log = logging.getLogger("sheet")

P = ParamSpec("P")
T = TypeVar("T")
Order = dict[str, str]


class SheetUnavailable(Exception):
    pass


def retry(func: Callable[P, T]) -> Callable[P, T]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        delay = config.RETRY_DELAY
        attempt = 0
        while True:
            attempt += 1
            try:
                return func(*args, **kwargs)
            except APIError as e:
                code = e.response.status_code
                if code not in config.RETRY_CODES:
                    log.error("%s: ошибка API %s", func.__name__, code)
                    raise
                reason = f"API {code}"
            except (ConnectionError, Timeout) as e:
                reason = type(e).__name__
            if attempt == config.RETRY_ATTEMPTS:
                log.error("%s: %s, попытки кончились", func.__name__, reason)
                raise SheetUnavailable(reason)
            log.warning("%s: %s, повтор через %s с", func.__name__, reason, delay)
            time.sleep(delay)
            delay = min(delay * 2, config.RETRY_MAX_DELAY)
    return wrapper


def now() -> str:
    return datetime.now(config.TZ).strftime(config.DATETIME_FORMAT)


def col(headers: list[str], name: str, sheet: str = config.SHEET_ORDERS) -> int:
    try:
        return headers.index(name) + 1
    except ValueError:
        raise KeyError(f"Нет столбца «{name}» на листе {sheet}") from None


class SheetRepository:
    def __init__(self, spreadsheet_id: str = config.SPREADSHEET_ID,
                 credentials_path: str = config.GOOGLE_CREDENTIALS) -> None:
        self._book = gspread.service_account(filename=credentials_path).open_by_key(spreadsheet_id)
        self._orders = self._book.worksheet(config.SHEET_ORDERS)
        self._journal = self._book.worksheet(config.SHEET_JOURNAL)
        self._dicts = self._book.worksheet(config.SHEET_DICTS)
        self._id_lock = threading.Lock()
        self._orders_headers = self._row1(self._orders)
        self._journal_headers = self._row1(self._journal)
        self._last_num = self._max_journal_num()
        log.info("Подключено к таблице «%s», последний ID %s", self._book.title, self._format_id(self._last_num))

    @staticmethod
    @retry
    def _row1(ws):
        return ws.row_values(1)

    def _with_headers(self, ws, attr, func):
        try:
            return func(getattr(self, attr))
        except KeyError:
            log.info("Заголовки листа «%s» изменились, перечитываю", ws.title)
            setattr(self, attr, self._row1(ws))
            return func(getattr(self, attr))

    @staticmethod
    def _format_id(num):
        return f"{config.ID_PREFIX}{num:0{config.ID_DIGITS}d}"

    @retry
    def _journal_ids(self, col_num):
        return self._journal.col_values(col_num)[1:]

    def _max_journal_num(self):
        ids = self._with_headers(self._journal, "_journal_headers",
                                 lambda h: self._journal_ids(col(h, config.COL_ID, config.SHEET_JOURNAL)))
        nums = [int(m.group(1)) for m in (config.ID_RE.match(str(i)) for i in ids) if m]
        return max(nums, default=0)

    @retry
    def _all(self):
        values = self._orders.get_all_values()
        self._orders_headers = values[0]
        return values[0], values[1:]

    @staticmethod
    def _row_dict(headers, row):
        row = row + [""] * (len(headers) - len(row))
        return {h: v for h, v in zip(headers, row) if h}

    @retry
    def _append_raw(self, ws, values):
        ws.append_row(values, value_input_option=ValueInputOption.raw, table_range="A1")

    @retry
    def _write_cell(self, row_num, col_num, value):
        self._orders.update([[value]], rowcol_to_a1(row_num, col_num), value_input_option=ValueInputOption.raw)

    def journal(self, tg_id: int | str, action: str, order_id: str) -> None:
        data = {
            config.JOURNAL_TIME: now(),
            config.COL_TG_ID: str(tg_id),
            config.JOURNAL_ACTION: action,
            config.COL_ID: order_id,
        }
        self._append_raw(self._journal, [data.get(h, "") for h in self._journal_headers])

    def create_order(self, data: Order) -> str:
        row = dict(data)
        row[config.COL_CREATED] = now()
        row.setdefault(config.COL_STATUS, config.STATUS_NEW)
        headers = self._orders_headers = self._row1(self._orders)
        col(headers, config.COL_ID)
        # ID выдаётся из счётчика в памяти: рассчитано на один процесс бота
        with self._id_lock:
            self._last_num += 1
            order_id = row[config.COL_ID] = self._format_id(self._last_num)
            try:
                self._append_raw(self._orders, [row.get(h, "") for h in headers])
            except SheetUnavailable:
                if self.find_order(order_id) is None:
                    raise
        self.journal(row.get(config.COL_TG_ID, ""), config.ACTION_CREATED, order_id)
        log.info("Создана заявка %s", order_id)
        return order_id

    def _find_row(self, order_id):
        headers, rows = self._all()
        id_idx = col(headers, config.COL_ID) - 1
        for i, row in enumerate(rows, start=2):
            if len(row) > id_idx and row[id_idx] == order_id:
                return i, headers, self._row_dict(headers, row)
        return None, headers, None

    def find_order(self, order_id: str) -> Order | None:
        _, _, order = self._find_row(order_id)
        log.info("Поиск %s: %s", order_id, "найдена" if order else "не найдена")
        return order

    def update_field(self, order_id: str, column: str, value: str, tg_id: int | str | None = None) -> None:
        row_num, headers, order = self._find_row(order_id)
        if row_num is None or order is None:
            raise LookupError(order_id)
        self._write_cell(row_num, col(headers, column), value)
        self.journal(tg_id or order.get(config.COL_TG_ID, ""), config.ACTION_UPDATED, order_id)
        log.info("Заявка %s: «%s» = %r (строка %s)", order_id, column, value, row_num)

    def delete_order(self, order_id: str, tg_id: int | str | None = None) -> None:
        row_num, _, order = self._find_row(order_id)
        if row_num is None or order is None:
            raise LookupError(order_id)
        retry(self._orders.delete_rows)(row_num)
        self.journal(tg_id or order.get(config.COL_TG_ID, ""), config.ACTION_DELETED, order_id)
        log.info("Удалена заявка %s (строка %s)", order_id, row_num)

    def all_orders(self) -> list[Order]:
        headers, rows = self._all()
        id_idx = col(headers, config.COL_ID) - 1
        return [self._row_dict(headers, r) for r in rows if len(r) > id_idx and r[id_idx]]

    def user_orders(self, tg_id: int | str, limit: int | None = None) -> list[Order]:
        orders = [o for o in self.all_orders() if o.get(config.COL_TG_ID) == str(tg_id)]
        orders.reverse()
        return orders[:limit] if limit else orders

    def last_order(self, tg_id: int | str) -> Order | None:
        orders = self.user_orders(tg_id, 1)
        return orders[0] if orders else None

    @retry
    def _dict_values(self):
        return self._dicts.get_all_values()

    def dictionaries(self) -> dict[str, Any]:
        values = self._dict_values()
        headers, rows = values[0], values[1:]
        t, s, st = (col(headers, n, config.SHEET_DICTS) - 1
                    for n in (config.DICT_TYPE, config.DICT_SUBTYPE, config.DICT_STATUS))
        subtypes = {}
        statuses = []
        for r in rows:
            r = r + [""] * (len(headers) - len(r))
            if r[t].strip():
                lst = subtypes.setdefault(r[t].strip(), [])
                if r[s].strip():
                    lst.append(r[s].strip())
            if r[st].strip():
                statuses.append(r[st].strip())
        return {"subtypes": subtypes, "statuses": statuses}


class AsyncSheetRepository:
    def __init__(self, repo: SheetRepository | None = None) -> None:
        self._repo = repo or SheetRepository()

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._repo, name)
        if not callable(attr):
            return attr

        async def call(*args, **kwargs):
            return await asyncio.to_thread(attr, *args, **kwargs)
        return call
