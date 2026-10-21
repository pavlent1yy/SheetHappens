from aiogram import Router
from aiogram.types import Message

from app import texts
from app.bot import keyboards

router = Router(name="fallback")


@router.message()
async def unknown(message: Message) -> None:
    await message.answer(texts.UNKNOWN, reply_markup=keyboards.main_menu())
