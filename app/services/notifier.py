import asyncio
import html
import json
import logging

from aiogram import Bot

from app import config, texts
from app.repositories.sheet_repository import SheetUnavailable
from app.services.orders import OrderService

log = logging.getLogger("notifier")


class StatusNotifier:
    def __init__(self, bot: Bot, orders: OrderService) -> None:
        self._bot = bot
        self._orders = orders
        self._file = config.NOTIFY_STATE_FILE
        self._known: dict[str, str] | None = self._load()

    def _load(self) -> dict[str, str] | None:
        try:
            return json.loads(self._file.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None

    def _save(self) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._known, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._file)

    async def run(self) -> None:
        log.info("Уведомления о статусах: проверка раз в %s с", config.NOTIFY_INTERVAL)
        while True:
            try:
                await self.check()
            except SheetUnavailable:
                log.warning("Таблица недоступна, проверка статусов пропущена")
            except Exception:
                log.exception("Ошибка проверки статусов")
            await asyncio.sleep(config.NOTIFY_INTERVAL)

    async def check(self) -> None:
        orders = await self._orders.all_orders()
        current = {o[config.COL_ID]: o.get(config.COL_STATUS, "") for o in orders}
        if self._known is None:
            self._known = current
            self._save()
            log.info("Первый запуск: запомнил статусы %s заявок без рассылки", len(current))
            return
        for order in orders:
            order_id = order[config.COL_ID]
            prev = self._known.get(order_id)
            status = current[order_id]
            self._known[order_id] = status
            if prev is not None and prev != status:
                self._save()
                await self._notify(order)
        for gone in set(self._known) - set(current):
            del self._known[gone]
        self._save()

    async def _notify(self, order: dict[str, str]) -> None:
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
