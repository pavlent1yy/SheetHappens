import asyncio
import html
import logging

from aiogram import Bot

from app import config, texts
from app.repositories.sheet_repository import Order, SheetUnavailable
from app.services.orders import OrderService

log = logging.getLogger("notifier")


class StatusNotifier:
    def __init__(self, bot: Bot, orders: OrderService) -> None:
        self._bot = bot
        self._orders = orders

    async def run(self) -> None:
        log.info("Уведомления о статусах: проверка кнопки раз в %s с", config.NOTIFY_INTERVAL)
        while True:
            try:
                if await self._orders.send_requested():
                    await self.publish()
            except SheetUnavailable:
                log.warning("Таблица недоступна, проверка статусов пропущена")
            except Exception:
                log.exception("Ошибка рассылки статусов")
            await asyncio.sleep(config.NOTIFY_INTERVAL)

    async def publish(self) -> None:
        changed = [o for o in await self._orders.all_orders()
                   if o.get(config.COL_STATUS) and o.get(config.COL_STATUS) != o.get(config.COL_CLIENT_STATUS)]
        await self._orders.update_many(
            {o[config.COL_ID]: {config.COL_CLIENT_STATUS: o[config.COL_STATUS]} for o in changed})
        await self._orders.finish_send()
        for order in changed:
            await self._notify(order)
        log.info("Рассылка по кнопке: изменённых статусов %s", len(changed))

    async def _notify(self, order: Order) -> None:
        text = texts.STATUS_CHANGED.format(
            id=order[config.COL_ID], status=html.escape(order.get(config.COL_STATUS, "")))
        comment = order.get(config.COL_MANAGER_COMMENT, "")
        if comment:
            text += texts.STATUS_COMMENT.format(comment=html.escape(comment))
        try:
            await self._bot.send_message(int(order[config.COL_TG_ID]), text)
            log.info("Уведомление: %s → %s", order[config.COL_ID], order.get(config.COL_STATUS))
        except Exception as e:
            log.warning("Не удалось уведомить по заявке %s: %s", order[config.COL_ID], e)
