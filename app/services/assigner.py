import asyncio
import html
import logging
from collections import Counter
from datetime import datetime

from aiogram import Bot

from app import config, texts
from app.bot.formatting import order_summary
from app.repositories.sheet_repository import Order, SheetUnavailable, now
from app.services.managers import Manager, ManagerService, assign_due
from app.services.orders import OrderService

log = logging.getLogger("assigner")


class OrderAssigner:
    def __init__(self, bot: Bot, orders: OrderService, managers: ManagerService) -> None:
        self._bot = bot
        self._orders = orders
        self._managers = managers
        self._warned_nobody = False

    async def run(self) -> None:
        log.info("Распределение заявок: через %s с после создания, проверка раз в %s с",
                 config.ASSIGN_DELAY, config.ASSIGN_INTERVAL)
        while True:
            try:
                await self.assign()
            except SheetUnavailable:
                log.warning("Таблица недоступна, распределение пропущено")
            except Exception:
                log.exception("Ошибка распределения заявок")
            await asyncio.sleep(config.ASSIGN_INTERVAL)

    async def assign(self) -> None:
        moment = datetime.now(config.TZ)
        orders = await self._orders.all_orders()
        pending = [o for o in orders
                   if not o.get(config.COL_MANAGER)
                   and o.get(config.COL_STATUS) == config.STATUS_NEW
                   and assign_due(o.get(config.COL_CREATED, ""), moment)]
        if not pending:
            return
        staff = await self._managers.on_shift(moment)
        if not staff:
            if not self._warned_nobody:
                log.warning("Нет менеджеров на смене, ждут распределения: %s", len(pending))
                self._warned_nobody = True
            return
        self._warned_nobody = False
        load = Counter(o.get(config.COL_MANAGER) for o in orders
                       if o.get(config.COL_STATUS) in config.EDITABLE_STATUSES)
        picks: list[tuple[Order, Manager]] = []
        for order in pending:
            manager = min(staff, key=lambda m: load[m.name])
            load[manager.name] += 1
            picks.append((order, manager))
        stamp = now()
        await self._orders.update_many(
            {o[config.COL_ID]: {config.COL_MANAGER: m.name, config.COL_ASSIGNED: stamp} for o, m in picks})
        for order, manager in picks:
            await self._notify(order, manager)

    async def _notify(self, order: Order, manager: Manager) -> None:
        assert manager.tg_id
        text = texts.MANAGER_ASSIGNED.format(
            id=order[config.COL_ID], user=html.escape(order.get(config.COL_USERNAME, "")), summary=order_summary(order))
        try:
            await self._bot.send_message(manager.tg_id, text)
            log.info("Заявка %s назначена: %s", order[config.COL_ID], manager.name)
        except Exception as e:
            log.warning("Заявка %s назначена %s, но уведомить не удалось: %s", order[config.COL_ID], manager.name, e)
