from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app import texts
from app.bot import keyboards

router = Router(name="menu")


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.START, reply_markup=keyboards.main_menu())


@router.message(F.text == texts.BTN_CANCEL)
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.CANCELLED, reply_markup=keyboards.main_menu())


async def show_menu(message: Message, state: FSMContext, text: str = texts.MENU) -> None:
    await state.clear()
    await message.answer(text, reply_markup=keyboards.main_menu())
