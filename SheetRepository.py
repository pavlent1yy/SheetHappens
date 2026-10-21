import asyncio
import functools
import logging
import threading
import time
from datetime import datetime

import gspread
from gspread.exceptions import APIError
from gspread.utils import ValueInputOption, a1_range_to_grid_range, rowcol_to_a1

import config

log = logging.getLogger("sheet")


def retry(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        delay = config.RETRY_DELAY
        for attempt in range(1, config.RETRY_ATTEMPTS + 1):
            try:
                return func(*args, **kwargs)
            except APIError as e:
                code = e.response.status_code
                if code not in config.RETRY_CODES or attempt == config.RETRY_ATTEMPTS:
                    log.error("%s: ошибка API %s", func.__name__, code)
                    raise
                log.warning("%s: API %s, повтор через %s с", func.__name__, code, delay)
                time.sleep(delay)
                delay = min(delay * 2, config.RETRY_MAX_DELAY)
    return wrapper


def now():
    return datetime.now(config.TZ).strftime(config.DATETIME_FORMAT)


class SheetRepository:
    def __init__(self, spreadsheet_id=config.SPREADSHEET_ID, credentials_path=config.GOOGLE_CREDENTIALS):
        self._book = gspread.service_account(filename=credentials_path).open_by_key(spreadsheet_id)
        self._orders = self._book.worksheet(config.SHEET_ORDERS)
        self._journal = self._book.worksheet(config.SHEET_JOURNAL)
        self._dicts = self._book.worksheet(config.SHEET_DICTS)
        self._lock = threading.Lock()
        log.info("Подключено к таблице «%s»", self._book.title)

    @staticmethod
    def _col(headers, name, sheet=config.SHEET_ORDERS):
        try:
            return headers.index(name) + 1
        except ValueError:
            raise KeyError(f"Нет столбца «{name}» на листе {sheet}") from None

    @staticmethod
    def _row_dict(headers, row):
        row = row + [""] * (len(headers) - len(row))
        return {h: v for h, v in zip(headers, row) if h}

    @retry
    def _all(self):
        values = self._orders.get_all_values()
        return values[0], values[1:]

    @retry
    def _headers(self):
        return self._orders.row_values(1)

    @retry
    def _order_ids(self, headers):
        return self._orders.col_values(self._col(headers, config.COL_ID))

    @retry
    def _next_id(self, headers):
        ids = self._order_ids(headers)[1:]
        j_headers = self._journal.row_values(1)
        ids += self._journal.col_values(self._col(j_headers, config.COL_ID, config.SHEET_JOURNAL))[1:]
        nums = [int(m.group(1)) for m in (config.ID_RE.match(str(i)) for i in ids) if m]
        return f"{config.ID_PREFIX}{max(nums, default=0) + 1:0{config.ID_DIGITS}d}"

    @retry
    def _append(self, ws, headers, data):
        res = ws.append_row([data.get(h, "") for h in headers],
                            value_input_option=ValueInputOption.raw, table_range="A1")
        rng = res["updates"]["updatedRange"].split("!")[-1]
        return a1_range_to_grid_range(rng)["startRowIndex"] + 1

    @retry
    def _write_cell(self, row_num, col_num, value):
        self._orders.update([[value]], rowcol_to_a1(row_num, col_num), value_input_option=ValueInputOption.raw)

    def journal(self, tg_id, action, order_id):
        headers = retry(self._journal.row_values)(1)
        self._append(self._journal, headers, {
            config.JOURNAL_TIME: now(),
            config.COL_TG_ID: str(tg_id),
            config.JOURNAL_ACTION: action,
            config.COL_ID: order_id,
        })

    def create_order(self, data):
        with self._lock:
            headers = self._headers()
            row = dict(data)
            row[config.COL_ID] = self._next_id(headers)
            row[config.COL_CREATED] = now()
            row.setdefault(config.COL_STATUS, config.STATUS_NEW)
            row_num = self._append(self._orders, headers, row)
            order_id = self._resolve_duplicate(headers, row_num, row[config.COL_ID])
            self.journal(row.get(config.COL_TG_ID, ""), config.ACTION_CREATED, order_id)
        log.info("Создана заявка %s (строка %s)", order_id, row_num)
        return order_id

    def _resolve_duplicate(self, headers, row_num, order_id):
        id_col = self._col(headers, config.COL_ID)
        while True:
            ids = self._order_ids(headers)
            first = ids.index(order_id) + 1
            if first == row_num:
                return order_id
            log.warning("ID %s занят строкой %s, выдаю новый", order_id, first)
            order_id = self._next_id(headers)
            self._write_cell(row_num, id_col, order_id)

    def _find_row(self, order_id):
        headers, rows = self._all()
        id_idx = self._col(headers, config.COL_ID) - 1
        for i, row in enumerate(rows, start=2):
            if len(row) > id_idx and row[id_idx] == order_id:
                return i, headers, self._row_dict(headers, row)
        return None, headers, None

    @retry
    def _id_at(self, row_num, headers):
        return self._orders.cell(row_num, self._col(headers, config.COL_ID)).value

    def _locate(self, order_id):
        for _ in range(config.RETRY_ATTEMPTS):
            row_num, headers, order = self._find_row(order_id)
            if order is None:
                raise LookupError(order_id)
            if self._id_at(row_num, headers) == order_id:
                return row_num, headers, order
            log.warning("Строка заявки %s сдвинулась, ищу заново", order_id)
        raise RuntimeError(f"Не удалось зафиксировать строку заявки {order_id}")

    def find_order(self, order_id):
        _, _, order = self._find_row(order_id)
        log.info("Поиск %s: %s", order_id, "найдена" if order else "не найдена")
        return order

    def update_field(self, order_id, column, value, tg_id=None):
        with self._lock:
            row_num, headers, order = self._locate(order_id)
            self._write_cell(row_num, self._col(headers, column), value)
            self.journal(tg_id or order.get(config.COL_TG_ID, ""), config.ACTION_UPDATED, order_id)
        log.info("Заявка %s: «%s» = %r (строка %s)", order_id, column, value, row_num)

    def delete_order(self, order_id, tg_id=None):
        with self._lock:
            row_num, _, order = self._locate(order_id)
            retry(self._orders.delete_rows)(row_num)
            self.journal(tg_id or order.get(config.COL_TG_ID, ""), config.ACTION_DELETED, order_id)
        log.info("Удалена заявка %s (строка %s)", order_id, row_num)

    def user_orders(self, tg_id, limit=None):
        headers, rows = self._all()
        orders = [self._row_dict(headers, r) for r in rows]
        orders = [o for o in orders if o.get(config.COL_TG_ID) == str(tg_id)]
        orders.reverse()
        return orders[:limit] if limit else orders

    def last_order(self, tg_id):
        orders = self.user_orders(tg_id, 1)
        return orders[0] if orders else None

    @retry
    def dictionaries(self):
        values = self._dicts.get_all_values()
        headers, rows = values[0], values[1:]
        t, s, st = (self._col(headers, n, config.SHEET_DICTS) - 1
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
    def __init__(self, repo=None):
        self._repo = repo or SheetRepository()

    def __getattr__(self, name):
        attr = getattr(self._repo, name)
        if not callable(attr):
            return attr

        async def call(*args, **kwargs):
            return await asyncio.to_thread(attr, *args, **kwargs)
        return call
