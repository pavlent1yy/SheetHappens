from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app import texts
from app.bot import keyboards
from app.services.managers import ManagerService

router = Router(name="menu")


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, managers: ManagerService) -> None:
    await state.clear()
    await message.answer(texts.START, reply_markup=keyboards.main_menu())
    if message.from_user:
        name = await managers.register(message.from_user.username, message.from_user.id)
        if name:
            await message.answer(texts.MANAGER_REGISTERED.format(name=name))


@router.message(F.text == texts.BTN_CANCEL)
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.CANCELLED, reply_markup=keyboards.main_menu())


async def show_menu(message: Message, state: FSMContext, text: str = texts.MENU) -> None:
    await state.clear()
    await message.answer(text, reply_markup=keyboards.main_menu())
