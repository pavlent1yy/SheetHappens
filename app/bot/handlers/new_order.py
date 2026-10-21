import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import Message

from app import config, texts
from app.bot import keyboards
from app.bot.formatting import summary
from app.bot.handlers.menu import show_menu
from app.bot.states import NewOrder
from app.repositories.sheet_repository import SheetUnavailable
from app.services import validation
from app.services.dictionaries import DictionaryService
from app.services.orders import OrderService
from app.services.photos import PhotoStorage

log = logging.getLogger("bot.new_order")
router = Router(name="new_order")

STEPS: list[State] = [
    NewOrder.type, NewOrder.subtype, NewOrder.weight, NewOrder.price,
    NewOrder.src, NewOrder.dst, NewOrder.comment, NewOrder.photo, NewOrder.confirm,
]
TEXT_STEPS = {
    NewOrder.weight: ("weight", validation.number),
    NewOrder.price: ("price", validation.number),
    NewOrder.src: ("src", validation.text),
    NewOrder.dst: ("dst", validation.text),
}
PROMPTS = {
    NewOrder.weight: texts.ASK_WEIGHT,
    NewOrder.price: texts.ASK_PRICE,
    NewOrder.src: texts.ASK_FROM,
    NewOrder.dst: texts.ASK_TO,
}


async def ask(step: State, message: Message, state: FSMContext, dicts: DictionaryService) -> None:
    await state.set_state(step)
    data = await state.get_data()
    if step == NewOrder.type:
        types = (await dicts.get()).types
        if not types:
            await show_menu(message, state, texts.NO_TYPES)
            return
        await message.answer(texts.ASK_TYPE, reply_markup=keyboards.choices(types))
    elif step == NewOrder.subtype:
        subtypes = (await dicts.get()).subtypes.get(data.get("type", ""), [])
        await message.answer(texts.ASK_SUBTYPE, reply_markup=keyboards.choices(subtypes))
    elif step == NewOrder.comment:
        await message.answer(texts.ASK_COMMENT, reply_markup=keyboards.step(skip=True))
    elif step == NewOrder.photo:
        await message.answer(texts.ASK_PHOTO, reply_markup=keyboards.step(skip=True))
    elif step == NewOrder.confirm:
        await message.answer(texts.ASK_CONFIRM.format(summary=summary(data)), reply_markup=keyboards.confirm())
    else:
        await message.answer(PROMPTS[step], reply_markup=keyboards.step())


async def next_step(message: Message, state: FSMContext, dicts: DictionaryService) -> None:
    current = await state.get_state()
    idx = next(i for i, s in enumerate(STEPS) if s.state == current)
    await ask(STEPS[idx + 1], message, state, dicts)


@router.message(F.text == texts.BTN_NEW)
async def start(message: Message, state: FSMContext, dicts: DictionaryService) -> None:
    await state.clear()
    await ask(NewOrder.type, message, state, dicts)


@router.message(NewOrder(), F.text == texts.BTN_BACK)
async def back(message: Message, state: FSMContext, dicts: DictionaryService) -> None:
    current = await state.get_state()
    idx = next(i for i, s in enumerate(STEPS) if s.state == current)
    if idx == 0:
        await show_menu(message, state)
    else:
        await ask(STEPS[idx - 1], message, state, dicts)


@router.message(NewOrder.type, F.text)
async def got_type(message: Message, state: FSMContext, dicts: DictionaryService) -> None:
    if message.text not in (await dicts.get()).types:
        await message.answer(texts.PICK_FROM_BUTTONS)
        return
    await state.update_data(type=message.text, subtype=None)
    await next_step(message, state, dicts)


@router.message(NewOrder.subtype, F.text)
async def got_subtype(message: Message, state: FSMContext, dicts: DictionaryService) -> None:
    data = await state.get_data()
    if message.text not in (await dicts.get()).subtypes.get(data.get("type", ""), []):
        await message.answer(texts.PICK_FROM_BUTTONS)
        return
    await state.update_data(subtype=message.text)
    await next_step(message, state, dicts)


@router.message(NewOrder.weight, F.text)
@router.message(NewOrder.price, F.text)
@router.message(NewOrder.src, F.text)
@router.message(NewOrder.dst, F.text)
async def got_text(message: Message, state: FSMContext, dicts: DictionaryService) -> None:
    current = await state.get_state()
    key, check = next(v for s, v in TEXT_STEPS.items() if s.state == current)
    try:
        value = check(message.text or "")
    except validation.ValidationError as e:
        await message.answer(str(e))
        return
    await state.update_data({key: value})
    await next_step(message, state, dicts)


@router.message(NewOrder.comment, F.text)
async def got_comment(message: Message, state: FSMContext, dicts: DictionaryService) -> None:
    if message.text == texts.BTN_SKIP:
        await state.update_data(comment="")
    else:
        try:
            await state.update_data(comment=validation.text(message.text or ""))
        except validation.ValidationError as e:
            await message.answer(str(e))
            return
    await next_step(message, state, dicts)


@router.message(NewOrder.photo, F.text == texts.BTN_SKIP)
async def skip_photo(message: Message, state: FSMContext, dicts: DictionaryService) -> None:
    await state.update_data(photo=None)
    await next_step(message, state, dicts)


@router.message(NewOrder.photo, F.photo)
async def got_photo(message: Message, state: FSMContext, dicts: DictionaryService) -> None:
    assert message.photo
    await state.update_data(photo=message.photo[-1].file_id)
    await next_step(message, state, dicts)


@router.message(NewOrder.photo, F.document.mime_type.startswith("image/"))
async def got_photo_file(message: Message, state: FSMContext, dicts: DictionaryService) -> None:
    assert message.document
    await state.update_data(photo=message.document.file_id)
    await next_step(message, state, dicts)


@router.message(NewOrder.photo)
async def wrong_photo(message: Message) -> None:
    await message.answer(texts.EXPECT_PHOTO)


@router.message(NewOrder.confirm, F.text == texts.BTN_RESTART)
async def restart(message: Message, state: FSMContext, dicts: DictionaryService) -> None:
    await state.clear()
    await ask(NewOrder.type, message, state, dicts)


@router.message(NewOrder.confirm, F.text == texts.BTN_SEND)
async def send(message: Message, state: FSMContext, orders: OrderService, photos: PhotoStorage) -> None:
    data = await state.get_data()
    user = message.from_user
    assert user
    await state.set_state(None)
    try:
        order_id = await orders.create({
            config.COL_USERNAME: f"@{user.username}" if user.username else config.NO_USERNAME,
            config.COL_TG_ID: str(user.id),
            config.COL_TYPE: data["type"],
            config.COL_SUBTYPE: data["subtype"],
            config.COL_WEIGHT: data["weight"],
            config.COL_PRICE: data["price"],
            config.COL_FROM: data["src"],
            config.COL_TO: data["dst"],
            config.COL_COMMENT: data.get("comment", ""),
        })
    except SheetUnavailable:
        await state.set_state(NewOrder.confirm)
        raise
    text = texts.CREATED.format(id=order_id)
    if data.get("photo"):
        try:
            await orders.set_photo(order_id, await photos.save(data["photo"], order_id))
        except Exception:
            log.exception("Фото заявки %s не сохранено", order_id)
            text = texts.PHOTO_FAILED.format(id=order_id)
    await show_menu(message, state, text)


@router.message(NewOrder.confirm)
async def confirm_buttons(message: Message) -> None:
    await message.answer(texts.PICK_FROM_BUTTONS)


@router.message(NewOrder.type)
@router.message(NewOrder.subtype)
async def wrong_choice(message: Message) -> None:
    await message.answer(texts.PICK_FROM_BUTTONS)


@router.message(NewOrder())
async def wrong_text(message: Message) -> None:
    await message.answer(texts.EXPECT_TEXT)
