import asyncio
import contextlib
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app import config
from app.bot.handlers import build_router
from app.repositories.sheet_repository import SheetRepository
from app.services.assigner import OrderAssigner
from app.services.dictionaries import DictionaryService
from app.services.managers import ManagerService
from app.services.notifier import StatusNotifier
from app.services.orders import OrderService
from app.services.photos import PhotoStorage

log = logging.getLogger("main")


async def main() -> None:
    if not config.BOT_TOKEN or not config.SPREADSHEET_ID:
        raise SystemExit("В .env должны быть BOT_TOKEN и SPREADSHEET_ID")

    repo = await asyncio.to_thread(SheetRepository)
    session = AiohttpSession(proxy=config.PROXY_URL) if config.PROXY_URL else None
    bot = Bot(config.BOT_TOKEN, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    orders = OrderService(repo)
    managers = ManagerService(repo)

    dp = Dispatcher(storage=MemoryStorage())
    dp["orders"] = orders
    dp["managers"] = managers
    dp["dicts"] = DictionaryService(repo)
    dp["photos"] = PhotoStorage(bot)
    dp.include_router(build_router())

    background: list[asyncio.Task[None]] = []
    try:
        me = await bot.get_me()
        log.info("Бот @%s запущен, владелец: %s", me.username,
                 f"@{config.OWNER_USERNAME}" if config.OWNER_ENABLED and config.OWNER_USERNAME else "выключен")
        background = [
            asyncio.create_task(StatusNotifier(bot, orders).run()),
            asyncio.create_task(OrderAssigner(bot, orders, managers).run()),
        ]
        await dp.start_polling(bot)
    finally:
        for task in background:
            task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.gather(*background)
        await bot.session.close()
        log.info("Бот остановлен")


if __name__ == "__main__":
    logging.basicConfig(level=config.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Остановлено по Ctrl+C")
