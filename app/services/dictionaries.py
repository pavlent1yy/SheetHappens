import asyncio
import logging
import time
from dataclasses import dataclass

from app import config
from app.repositories.sheet_repository import SheetRepository

log = logging.getLogger("dicts")


@dataclass(frozen=True)
class Dictionaries:
    subtypes: dict[str, list[str]]
    statuses: list[str]

    @property
    def types(self) -> list[str]:
        return list(self.subtypes)


class DictionaryService:
    def __init__(self, repo: SheetRepository, ttl: int = config.DICTS_TTL) -> None:
        self._repo = repo
        self._ttl = ttl
        self._cached: Dictionaries | None = None
        self._loaded_at = 0.0
        self._lock = asyncio.Lock()

    async def get(self) -> Dictionaries:
        async with self._lock:
            if self._cached is None or time.monotonic() - self._loaded_at > self._ttl:
                raw = await asyncio.to_thread(self._repo.dictionaries)
                self._cached = Dictionaries(raw["subtypes"], raw["statuses"])
                self._loaded_at = time.monotonic()
                log.info("Справочники загружены: %s типов, %s статусов",
                         len(self._cached.subtypes), len(self._cached.statuses))
            return self._cached

    def invalidate(self) -> None:
        self._cached = None
