from app import config
from app.services.assigner import distribute
from app.services.managers import Manager


def staff(*names: str) -> list[Manager]:
    return [Manager(name=n, username="", tg_id=i, schedule={}) for i, n in enumerate(names, 1)]


def order(order_id: str, manager: str = "", status: str = config.STATUS_NEW) -> dict[str, str]:
    return {config.COL_ID: order_id, config.COL_MANAGER: manager, config.COL_STATUS: status}


def names(picks):
    return [m.name for _, m in picks]


def test_even_split_without_load():
    pending = [order(f"D-{i}") for i in range(4)]
    assert sorted(names(distribute(pending, staff("Аня", "Боря"), pending))) == ["Аня", "Аня", "Боря", "Боря"]


def test_least_loaded_first():
    busy = [order("D-a", "Аня"), order("D-b", "Аня", config.STATUS_ACCEPTED)]
    pending = [order("D-1"), order("D-2"), order("D-3")]
    assert names(distribute(pending, staff("Аня", "Боря"), busy + pending)) == ["Боря", "Боря", "Аня"]


def test_finished_orders_do_not_count():
    done = [order(f"D-{i}", "Аня", "Доставлена") for i in range(5)]
    pending = [order("D-new")]
    assert names(distribute(pending, staff("Аня", "Боря"), done + pending)) == ["Аня"]
