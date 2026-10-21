import asyncio
import logging
import sys

from app import config
from app.repositories.sheet_repository import AsyncSheetRepository

logging.basicConfig(level=config.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

CLEAN = "--clean" in sys.argv

samples = [
    ("Документы", "Конверт", "0,2", "1000", "Москва, Тверская 1", "Москва, Арбат 5"),
    ("Посылка", "Малая", "2,5", "3500", "Москва, Ленина 10", "Химки, Мира 3"),
    ("Груз", "До 50 кг", "42", "15000", "Москва, склад 7", "Тула, Советская 12"),
]


async def main():
    repo = AsyncSheetRepository()
    ids = []
    try:
        for kind, sub, weight, price, src, dst in samples:
            ids.append(await repo.create_order({
                "Telegram": "@test_user",
                "Telegram ID": "123456789",
                "Тип": kind,
                "Подтип": sub,
                "Вес, кг": weight,
                "Объявл. стоимость, ₽": price,
                "Откуда": src,
                "Куда": dst,
            }))

        print(await repo.find_order(ids[1]))

        await repo.update_field(ids[-1], "Телефон получателя", "+7 900 123-45-67")
        print(await repo.find_order(ids[-1]))
    finally:
        if CLEAN:
            for order_id in ids:
                await repo.delete_order(order_id)


asyncio.run(main())
