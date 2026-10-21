import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from app import config
from app.repositories.sheet_repository import SheetRepository

log = logging.getLogger("managers")

Shift = tuple[time, time]


@dataclass(frozen=True)
class Manager:
    name: str
    username: str
    tg_id: int | None
    schedule: dict[int, list[Shift]]

    def on_shift(self, moment: datetime) -> bool:
        t = moment.time()
        today = self.schedule.get(moment.weekday(), [])
        yesterday = self.schedule.get((moment.weekday() - 1) % 7, [])
        return (any(start <= t < end if start < end else t >= start for start, end in today)
                or any(start > end and t < end for start, end in yesterday))


def parse_shifts(value: str) -> list[Shift]:
    shifts = []
    for part in value.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        start, end = (datetime.strptime(x.strip(), "%H:%M").time() for x in part.split("-"))
        shifts.append((start, end))
    return shifts


def parse_manager(row: dict[str, str]) -> Manager | None:
    name = row.get(config.MGR_NAME, "").strip()
    if not name:
        return None
    schedule = {}
    for day, column in enumerate(config.WEEKDAYS):
        try:
            schedule[day] = parse_shifts(row.get(column, ""))
        except ValueError:
            log.warning("Менеджер %s: не разобрал график «%s» (%s), формат 09:00-18:00",
                        name, row.get(column), column)
    tg_id = row.get(config.MGR_TG_ID, "").strip()
    return Manager(
        name=name,
        username=row.get(config.MGR_USERNAME, "").strip().lstrip("@").lower(),
        tg_id=int(tg_id) if tg_id.isdigit() else None,
        schedule=schedule,
    )


def created_at(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, config.DATETIME_FORMAT).replace(tzinfo=config.TZ)
    except ValueError:
        return None


def assign_due(created: str, moment: datetime) -> bool:
    at = created_at(created)
    return at is not None and moment - at >= timedelta(seconds=config.ASSIGN_DELAY)


class ManagerService:
    def __init__(self, repo: SheetRepository) -> None:
        self._repo = repo

    async def all(self) -> list[Manager]:
        rows = await asyncio.to_thread(self._repo.managers)
        return [m for m in map(parse_manager, rows) if m]

    async def on_shift(self, moment: datetime) -> list[Manager]:
        return [m for m in await self.all() if m.tg_id and m.on_shift(moment)]

    async def register(self, username: str | None, tg_id: int) -> str | None:
        if not username:
            return None
        return await asyncio.to_thread(self._repo.set_manager_tg_id, username, tg_id)
