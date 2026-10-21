from datetime import datetime, time, timedelta

import pytest

from app import config
from app.services.managers import Manager, assign_due, parse_manager, parse_shifts

MON = datetime(2026, 10, 19, tzinfo=config.TZ)


def at(day: int, hh: int, mm: int = 0) -> datetime:
    return MON + timedelta(days=day, hours=hh, minutes=mm)


def manager(**days: str) -> Manager:
    m = parse_manager({config.MGR_NAME: "Аня", config.MGR_TG_ID: "1", **days})
    assert m
    return m


def test_parse_shifts():
    assert parse_shifts("09:00-13:00, 14:00-18:00") == [(time(9), time(13)), (time(14), time(18))]
    assert parse_shifts("") == []
    with pytest.raises(ValueError):
        parse_shifts("с утра")


@pytest.mark.parametrize("moment, expected", [
    (at(0, 8, 59), False),
    (at(0, 9), True),
    (at(0, 17, 59), True),
    (at(0, 18), False),
    (at(1, 12), False),
])
def test_day_shift(moment, expected):
    assert manager(Пн="09:00-18:00").on_shift(moment) is expected


@pytest.mark.parametrize("moment, expected", [
    (at(0, 21, 59), False),
    (at(0, 22), True),
    (at(0, 23, 59), True),
    (at(1, 0), True),
    (at(1, 5, 59), True),
    (at(1, 6), False),
    (at(2, 1), False),
])
def test_night_shift_crosses_midnight(moment, expected):
    assert manager(Пн="22:00-06:00").on_shift(moment) is expected


def test_night_shift_from_sunday_wraps_to_monday():
    assert manager(Вс="22:00-06:00").on_shift(at(0, 3)) is True


def test_bad_schedule_cell_is_day_off():
    m = manager(Пн="круглосуточно", Вт="09:00-18:00")
    assert not m.on_shift(at(0, 12))
    assert m.on_shift(at(1, 12))


def test_tg_id_and_username():
    m = parse_manager({config.MGR_NAME: "Аня", config.MGR_USERNAME: "@Anya", config.MGR_TG_ID: ""})
    assert m and m.username == "anya" and m.tg_id is None
    assert parse_manager({config.MGR_NAME: " "}) is None


def test_assign_due():
    created = at(0, 12).strftime(config.DATETIME_FORMAT)
    assert not assign_due(created, at(0, 12, 4))
    assert assign_due(created, at(0, 12, 5))
    assert not assign_due("мусор", at(0, 12, 5))
