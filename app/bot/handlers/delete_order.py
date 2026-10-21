from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app import config, texts
from app.bot import keyboards
from app.bot.formatting import order_summary
from app.bot.handlers.menu import show_menu
from app.bot.states import DeleteOrder
from app.services.orders import OrderNotFound, OrderService, WrongStatus

router = Router(name="delete_order")


@router.message(F.text == texts.BTN_DELETE)
async def start(message: Message, state: FSMContext, orders: OrderService) -> None:
    assert message.from_user
    await state.clear()
    try:
        order = await orders.last_deletable(message.from_user.id)
    except OrderNotFound:
        await show_menu(message, state, texts.DELETE_NONE)
        return
    except WrongStatus as e:
        await show_menu(message, state, texts.DELETE_IN_WORK.format(status=e.status))
        return
    order_id = order[config.COL_ID]
    await state.set_state(DeleteOrder.confirm)
    await state.update_data(order_id=order_id)
    await message.answer(texts.DELETE_CONFIRM.format(id=order_id, summary=order_summary(order)),
                         reply_markup=keyboards.yes_no())


@router.message(DeleteOrder.confirm, F.text == texts.BTN_YES)
async def confirm(message: Message, state: FSMContext, orders: OrderService) -> None:
    assert message.from_user
    order_id = (await state.get_data())["order_id"]
    try:
        await orders.delete_last(order_id, message.from_user.id)
    except OrderNotFound:
        await show_menu(message, state, texts.DELETE_CHANGED)
        return
    except WrongStatus as e:
        await show_menu(message, state, texts.DELETE_IN_WORK.format(status=e.status))
        return
    await show_menu(message, state, texts.DELETED.format(id=order_id))


@router.message(DeleteOrder.confirm, F.text == texts.BTN_NO)
async def decline(message: Message, state: FSMContext) -> None:
    await show_menu(message, state)


@router.message(DeleteOrder.confirm)
async def wrong(message: Message) -> None:
    await message.answer(texts.PICK_FROM_BUTTONS)
