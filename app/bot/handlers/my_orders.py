from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app import config, texts
from app.bot.handlers.menu import show_menu
from app.services.orders import OrderService

router = Router(name="my_orders")


@router.message(F.text == texts.BTN_MY)
async def my_orders(message: Message, state: FSMContext, orders: OrderService) -> None:
    assert message.from_user
    items = await orders.user_orders(message.from_user.id)
    if not items:
        await show_menu(message, state, texts.MY_EMPTY)
        return
    text = texts.MY_HEADER + "".join(
        texts.MY_ROW.format(
            id=o[config.COL_ID],
            created=o.get(config.COL_CREATED, ""),
            type=escape(o.get(config.COL_TYPE, "")),
            status=escape(o.get(config.COL_STATUS, "")),
        ) for o in items)
    await show_menu(message, state, text)
