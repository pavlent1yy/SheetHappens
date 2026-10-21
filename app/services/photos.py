import logging
import uuid

from aiogram import Bot

from app import config

log = logging.getLogger("photos")


class PhotoStorage:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def save(self, file_id: str, order_id: str) -> str:
        if config.PHOTO_CHAT_ID:
            return await self._to_chat(file_id, order_id)
        return await self._to_disk(file_id, order_id)

    async def _to_chat(self, file_id: str, order_id: str) -> str:
        msg = await self._bot.send_photo(config.PHOTO_CHAT_ID, file_id, caption=order_id)
        if msg.chat.username:
            link = f"https://t.me/{msg.chat.username}/{msg.message_id}"
        else:
            link = f"https://t.me/c/{str(msg.chat.id).removeprefix('-100')}/{msg.message_id}"
        log.info("Фото заявки %s отправлено в чат: %s", order_id, link)
        return link

    async def _to_disk(self, file_id: str, order_id: str) -> str:
        config.PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
        file = await self._bot.get_file(file_id)
        ext = (file.file_path or "").rsplit(".", 1)[-1] if file.file_path and "." in file.file_path else "jpg"
        name = f"{order_id}_{uuid.uuid4().hex[:8]}.{ext}"
        await self._bot.download_file(file.file_path or "", config.PHOTOS_DIR / name)
        log.info("Фото заявки %s сохранено: %s", order_id, name)
        return f"photos/{name}"
