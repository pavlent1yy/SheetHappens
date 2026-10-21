import asyncio
import logging
import sys

from app import config
from app.repositories.sheet_repository import SheetRepository
from app.services.orders import OrderService

logging.basicConfig(level=config.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

CLEAN = "--clean" in sys.argv

samples = [
    ("Документы", "Конверт", "0,2", "1000", "Москва, Тверская 1", "Москва, Арбат 5"),
    ("Посылка", "Малая", "2,5", "3500", "Москва, Ленина 10", "Химки, Мира 3"),
    ("Груз", "До 50 кг", "42", "15000", "Москва, склад 7", "Тула, Советская 12"),
]


async def main():
    repo = await asyncio.to_thread(SheetRepository)
    orders = OrderService(repo)
    ids = []
    try:
        for kind, sub, weight, price, src, dst in samples:
            ids.append(await orders.create({
                "Telegram": "@test_user",
                "Telegram ID": "123456789",
                "Тип": kind,
                "Подтип": sub,
                "Вес, кг": weight,
                "Объявл. стоимость, ₽": price,
                "Откуда": src,
                "Куда": dst,
            }))

        print(await asyncio.to_thread(repo.find_order, ids[1]))

        await asyncio.to_thread(repo.update_field, ids[-1], "Телефон получателя", "+7 900 123-45-67")
        print(await asyncio.to_thread(repo.find_order, ids[-1]))
    finally:
        if CLEAN:
            for order_id in ids:
                await asyncio.to_thread(repo.delete_order, order_id)


asyncio.run(main())
