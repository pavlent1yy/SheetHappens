from aiogram.filters import BaseFilter
from aiogram.types import Message

from app import config


class OwnerMode:
    active = config.OWNER_ENABLED


def is_owner_account(message: Message) -> bool:
    user = message.from_user
    return bool(config.OWNER_ENABLED and config.OWNER_USERNAME and user and user.username
                and user.username.lower() == config.OWNER_USERNAME)


class IsOwner(BaseFilter):
    def __init__(self, check_mode: bool = True) -> None:
        self.check_mode = check_mode

    async def __call__(self, message: Message) -> bool:
        return is_owner_account(message) and (OwnerMode.active or not self.check_mode)
