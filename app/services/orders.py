import asyncio
import logging
from collections import Counter
from dataclasses import dataclass

from app import config
from app.repositories.sheet_repository import Order, SheetRepository

log = logging.getLogger("orders")


class OrderNotFound(Exception):
    pass


class NotOwner(Exception):
    pass


class WrongStatus(Exception):
    def __init__(self, status: str) -> None:
        super().__init__(status)
        self.status = status


@dataclass(frozen=True)
class Stats:
    total: int
    clients: int
    by_status: dict[str, int]


class OrderService:
    def __init__(self, repo: SheetRepository) -> None:
        self._repo = repo

    async def create(self, data: Order) -> str:
        return await asyncio.to_thread(self._repo.create_order, data)

    async def set_photo(self, order_id: str, value: str) -> None:
        await asyncio.to_thread(self._repo.update_field, order_id, config.COL_PHOTO, value)

    async def user_orders(self, tg_id: int, limit: int = config.MY_ORDERS_LIMIT) -> list[Order]:
        return await asyncio.to_thread(self._repo.user_orders, tg_id, limit)

    async def get_own(self, order_id: str, tg_id: int, allowed: tuple[str, ...]) -> Order:
        order = await asyncio.to_thread(self._repo.find_order, order_id)
        if order is None:
            raise OrderNotFound(order_id)
        if order.get(config.COL_TG_ID) != str(tg_id):
            log.warning("Пользователь %s пытался открыть чужую заявку %s", tg_id, order_id)
            raise NotOwner(order_id)
        if order.get(config.COL_STATUS) not in allowed:
            raise WrongStatus(order.get(config.COL_STATUS, ""))
        return order

    async def update(self, order_id: str, tg_id: int, column: str, value: str) -> None:
        await self.get_own(order_id, tg_id, config.EDITABLE_STATUSES)
        await asyncio.to_thread(self._repo.update_field, order_id, column, value, tg_id)

    async def last_deletable(self, tg_id: int) -> Order:
        order = await asyncio.to_thread(self._repo.last_order, tg_id)
        if order is None:
            raise OrderNotFound("")
        if order.get(config.COL_STATUS) not in config.DELETABLE_STATUSES:
            raise WrongStatus(order.get(config.COL_STATUS, ""))
        return order

    async def delete_last(self, order_id: str, tg_id: int) -> None:
        last = await self.last_deletable(tg_id)
        if last.get(config.COL_ID) != order_id:
            raise OrderNotFound(order_id)
        await asyncio.to_thread(self._repo.delete_order, order_id, tg_id)

    async def all_orders(self) -> list[Order]:
        return await asyncio.to_thread(self._repo.all_orders)

    async def update_many(self, changes: dict[str, dict[str, str]]) -> None:
        await asyncio.to_thread(self._repo.update_many, changes)

    async def send_requested(self) -> bool:
        return await asyncio.to_thread(self._repo.send_requested)

    async def finish_send(self) -> None:
        await asyncio.to_thread(self._repo.finish_send)

    async def stats(self) -> Stats:
        orders = await self.all_orders()
        return Stats(
            total=len(orders),
            clients=len({o.get(config.COL_TG_ID) for o in orders}),
            by_status=dict(Counter(o.get(config.COL_STATUS, "") or "—" for o in orders)),
        )
