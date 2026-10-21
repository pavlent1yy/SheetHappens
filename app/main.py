import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app import config
from app.bot.handlers import build_router
from app.repositories.sheet_repository import SheetRepository
from app.services.dictionaries import DictionaryService
from app.services.notifier import StatusNotifier
from app.services.orders import OrderService
from app.services.photos import PhotoStorage

log = logging.getLogger("main")


async def main() -> None:
    logging.basicConfig(level=config.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not config.BOT_TOKEN or not config.SPREADSHEET_ID:
        raise SystemExit("В .env должны быть BOT_TOKEN и SPREADSHEET_ID")

    repo = await asyncio.to_thread(SheetRepository)
    session = AiohttpSession(proxy=config.PROXY_URL) if config.PROXY_URL else None
    bot = Bot(config.BOT_TOKEN, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    orders = OrderService(repo)

    dp = Dispatcher(storage=MemoryStorage())
    dp["orders"] = orders
    dp["dicts"] = DictionaryService(repo)
    dp["photos"] = PhotoStorage(bot)
    dp.include_router(build_router())

    notifier: asyncio.Task[None] | None = None
    try:
        me = await bot.get_me()
        log.info("Бот @%s запущен, владелец: %s", me.username,
                 f"@{config.OWNER_USERNAME}" if config.OWNER_ENABLED and config.OWNER_USERNAME else "выключен")
        notifier = asyncio.create_task(StatusNotifier(bot, orders).run())
        await dp.start_polling(bot)
    finally:
        if notifier:
            notifier.cancel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
