import os
import gspread
from dotenv import load_dotenv

load_dotenv()
gc = gspread.service_account(filename=os.getenv("GOOGLE_CREDENTIALS", "credits.json"))
sh = gc.open_by_key(os.environ["SPREADSHEET_ID"])

ORDERS = ["ID заявки", "Создана", "Telegram", "Telegram ID", "Тип", "Подтип",
          "Вес, кг", "Объявл. стоимость, ₽", "Откуда", "Куда", "Комментарий",
          "Фото", "Телефон получателя", "Статус", "Комментарий менеджера",
          "Статус для клиента", "Менеджер", "Назначена"]
DICTS = ["Тип", "Подтип", "", "Статус"]
LOG = ["Время", "Telegram ID", "Действие", "ID заявки"]
MANAGERS = ["Менеджер", "Telegram", "Telegram ID", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MANAGER_ROWS = [["Пример Менеджер", "username_без_собачки", "",
                 "09:00-18:00", "09:00-18:00", "09:00-18:00", "09:00-18:00", "09:00-18:00", "", ""]]

DICT_ROWS = [
    ["Документы", "Конверт", "", "Новая"],
    ["Документы", "Папка", "", "Принята"],
    ["Посылка", "Малая", "", "В пути"],
    ["Посылка", "Крупная", "", "Доставлена"],
    ["Груз", "До 50 кг", "", "Отменена"],
    ["Груз", "Паллета", "", ""],
    ["Груз", "Негабарит", "", ""],
]


def ensure_ws(title: str, headers: list[str]) -> gspread.Worksheet:
    try:
        ws = sh.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows=1000, cols=len(headers))
    if ws.col_count < len(headers):
        ws.add_cols(len(headers) - ws.col_count)
    ws.update([headers], "A1")
    ws.freeze(rows=1)
    ws.format("1:1", {"textFormat": {"bold": True},
                      "backgroundColor": {"red": 0.9, "green": 0.93, "blue": 0.96}})
    return ws


orders = ensure_ws("Заявки", ORDERS)
dicts = ensure_ws("Справочники", DICTS)
ensure_ws("Журнал", LOG)

managers = ensure_ws("Менеджеры", MANAGERS)

if len(dicts.get_all_values()) == 1:   # не затираем правки менеджера
    dicts.update(DICT_ROWS, "A2")
if len(managers.get_all_values()) == 1:
    managers.update(MANAGER_ROWS, "A2")

# Старые заявки: клиент уже знает текущий статус, повторно не уведомляем
rows = orders.get_all_values()[1:]
st, cst = ORDERS.index("Статус"), ORDERS.index("Статус для клиента")
fill = [[r[cst] if len(r) > cst and r[cst] else (r[st] if len(r) > st else "")] for r in rows]
if fill:
    orders.update(fill, gspread.utils.rowcol_to_a1(2, cst + 1))

try:
    control = sh.worksheet("Управление")
except gspread.WorksheetNotFound:
    control = sh.add_worksheet(title="Управление", rows=10, cols=2)
control.update([["Сохранить и отправить уведомления клиентам", False],
                ["Последняя отправка", control.acell("B2").value or ""]],
               "A1", value_input_option="USER_ENTERED")
control.format("A1:A2", {"textFormat": {"bold": True}})
sh.batch_update({"requests": [{
    "setDataValidation": {
        "range": {"sheetId": control.id, "startRowIndex": 0, "endRowIndex": 1,
                  "startColumnIndex": 1, "endColumnIndex": 2},
        "rule": {"condition": {"type": "BOOLEAN"}},
    }
}]})

# Выпадающий список статусов в столбце «Статус» — из справочника
status_col = ORDERS.index("Статус")
sh.batch_update({"requests": [{
    "setDataValidation": {
        "range": {"sheetId": orders.id, "startRowIndex": 1,
                  "startColumnIndex": status_col, "endColumnIndex": status_col + 1},
        "rule": {
            "condition": {"type": "ONE_OF_RANGE",
                          "values": [{"userEnteredValue": "='Справочники'!$D$2:$D"}]},
            "showCustomUi": True, "strict": True,
        },
    }
}]})

# Дефолтный «Лист1» больше не нужен
try:
    sh.del_worksheet(sh.worksheet("Лист1"))
except gspread.WorksheetNotFound:
    pass

print("Готово:", sh.url)