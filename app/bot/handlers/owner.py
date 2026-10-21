import time
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app import config, texts
from app.bot import keyboards
from app.bot.filters import IsOwner, OwnerMode
from app.bot.handlers.menu import show_menu
from app.services.dictionaries import DictionaryService
from app.services.orders import OrderService

router = Router(name="owner")


@router.message(Command("owner_on"), IsOwner(check_mode=False))
async def owner_on(message: Message) -> None:
    OwnerMode.active = True
    await message.answer(texts.OWNER_MODE_ON)


@router.message(Command("owner_off"), IsOwner())
async def owner_off(message: Message, state: FSMContext) -> None:
    OwnerMode.active = False
    await show_menu(message, state, texts.OWNER_MODE_OFF)


@router.message(Command("owner"), IsOwner())
async def panel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.OWNER_MENU, reply_markup=keyboards.owner_menu())


@router.message(F.text == texts.BTN_OWNER_STATS, IsOwner())
async def stats(message: Message, orders: OrderService) -> None:
    s = await orders.stats()
    rows = "".join(texts.OWNER_STATUS_ROW.format(status=escape(k), count=v) for k, v in s.by_status.items())
    await message.answer(texts.OWNER_STATS.format(total=s.total, clients=s.clients, statuses=rows))


@router.message(F.text == texts.BTN_OWNER_ORDERS, IsOwner())
async def last_orders(message: Message, orders: OrderService) -> None:
    items = (await orders.all_orders())[-config.OWNER_ORDERS_LIMIT:][::-1]
    if not items:
        await message.answer(texts.OWNER_ORDERS_EMPTY)
        return
    await message.answer("".join(
        texts.OWNER_ORDER_ROW.format(
            id=o[config.COL_ID],
            created=o.get(config.COL_CREATED, ""),
            user=escape(o.get(config.COL_USERNAME, "")),
            type=escape(o.get(config.COL_TYPE, "")),
            subtype=escape(o.get(config.COL_SUBTYPE, "")),
            status=escape(o.get(config.COL_STATUS, "")),
        ) for o in items).lstrip())


@router.message(F.text == texts.BTN_OWNER_DICTS, IsOwner())
async def reload_dicts(message: Message, dicts: DictionaryService) -> None:
    dicts.invalidate()
    d = await dicts.get()
    await message.answer(texts.OWNER_DICTS.format(types=len(d.types), statuses=len(d.statuses)))


@router.message(F.text == texts.BTN_OWNER_PING, IsOwner())
async def ping(message: Message, orders: OrderService) -> None:
    started = time.monotonic()
    await orders.all_orders()
    await message.answer(texts.OWNER_PING_OK.format(ms=int((time.monotonic() - started) * 1000)))


@router.message(F.text == texts.BTN_OWNER_EXIT, IsOwner())
async def exit_panel(message: Message, state: FSMContext) -> None:
    await show_menu(message, state)


@router.message(Command("owner", "owner_on", "owner_off"))
async def not_owner(message: Message) -> None:
    await message.answer(texts.OWNER_ONLY)
