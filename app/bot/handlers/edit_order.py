from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app import config, texts
from app.bot import keyboards
from app.bot.handlers.menu import show_menu
from app.bot.states import EditOrder
from app.services import validation
from app.services.orders import NotOwner, OrderNotFound, OrderService, WrongStatus

router = Router(name="edit_order")

FIELDS = {
    texts.BTN_FIELD_PHONE: (config.COL_PHONE, texts.ASK_PHONE, validation.phone),
    texts.BTN_FIELD_COMMENT: (config.COL_COMMENT, texts.ASK_NEW_COMMENT, validation.text),
}


async def ask_id(message: Message, state: FSMContext) -> None:
    await state.set_state(EditOrder.order_id)
    await message.answer(texts.ASK_EDIT_ID, reply_markup=keyboards.step(back=False))


def error_text(e: Exception) -> str:
    if isinstance(e, NotOwner):
        return texts.ERR_NOT_YOURS
    if isinstance(e, WrongStatus):
        return texts.ERR_NOT_EDITABLE.format(status=e.status)
    return texts.ERR_NOT_FOUND


@router.message(F.text == texts.BTN_EDIT)
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await ask_id(message, state)


@router.message(EditOrder.order_id, F.text)
async def got_id(message: Message, state: FSMContext, orders: OrderService) -> None:
    assert message.from_user
    order_id = (message.text or "").strip().upper()
    try:
        await orders.get_own(order_id, message.from_user.id, config.EDITABLE_STATUSES)
    except (OrderNotFound, NotOwner, WrongStatus) as e:
        await message.answer(error_text(e))
        return
    await state.update_data(order_id=order_id)
    await state.set_state(EditOrder.field)
    await message.answer(texts.ASK_EDIT_FIELD.format(id=order_id), reply_markup=keyboards.edit_fields())


@router.message(EditOrder.field, F.text == texts.BTN_BACK)
async def back_to_id(message: Message, state: FSMContext) -> None:
    await ask_id(message, state)


@router.message(EditOrder.field, F.text.in_(FIELDS))
async def got_field(message: Message, state: FSMContext) -> None:
    await state.update_data(field=message.text)
    await state.set_state(EditOrder.value)
    await message.answer(FIELDS[message.text or ""][1], reply_markup=keyboards.step())


@router.message(EditOrder.field)
async def wrong_field(message: Message) -> None:
    await message.answer(texts.PICK_FROM_BUTTONS)


@router.message(EditOrder.value, F.text == texts.BTN_BACK)
async def back_to_field(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(EditOrder.field)
    await message.answer(texts.ASK_EDIT_FIELD.format(id=data["order_id"]), reply_markup=keyboards.edit_fields())


@router.message(EditOrder.value, F.text)
async def got_value(message: Message, state: FSMContext, orders: OrderService) -> None:
    assert message.from_user
    data = await state.get_data()
    column, _, check = FIELDS[data["field"]]
    try:
        value = check(message.text or "")
    except validation.ValidationError as e:
        await message.answer(str(e))
        return
    try:
        await orders.update(data["order_id"], message.from_user.id, column, value)
    except (OrderNotFound, NotOwner, WrongStatus) as e:
        await show_menu(message, state, error_text(e))
        return
    await show_menu(message, state, texts.EDITED.format(id=data["order_id"]))


@router.message(EditOrder())
async def wrong_type(message: Message) -> None:
    await message.answer(texts.EXPECT_TEXT)
