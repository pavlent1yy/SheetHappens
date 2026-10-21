import logging

from aiogram import Router
from aiogram.filters import ExceptionTypeFilter
from aiogram.types import ErrorEvent

from app import texts
from app.repositories.sheet_repository import SheetUnavailable

log = logging.getLogger("bot.errors")
router = Router(name="errors")


@router.errors(ExceptionTypeFilter(SheetUnavailable))
async def sheet_unavailable(event: ErrorEvent) -> None:
    log.warning("Таблица недоступна: %s", event.exception)
    if event.update.message:
        await event.update.message.answer(texts.SHEET_UNAVAILABLE)


@router.errors()
async def unexpected(event: ErrorEvent) -> None:
    log.exception("Необработанная ошибка", exc_info=event.exception)
    if event.update.message:
        await event.update.message.answer(texts.INTERNAL_ERROR)
