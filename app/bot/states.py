from aiogram.fsm.state import State, StatesGroup


class NewOrder(StatesGroup):
    type = State()
    subtype = State()
    weight = State()
    price = State()
    src = State()
    dst = State()
    comment = State()
    photo = State()
    confirm = State()


class EditOrder(StatesGroup):
    order_id = State()
    field = State()
    value = State()


class DeleteOrder(StatesGroup):
    confirm = State()
